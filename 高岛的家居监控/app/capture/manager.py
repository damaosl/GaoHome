"""独立抓包模式管理：以子进程启动 / 停止 mitmdump"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..config import HOST, PORT

CAPTURE_PORT = 8888
ADDON_PATH = Path(__file__).with_name("addon.py")
# mitmproxy 自动生成的 CA 证书位置（HTTPS 解密需在设备上安装）
CA_CERT_PATH = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"


def _mitmdump_cmd() -> list:
    """定位 mitmdump 可执行文件（pip 安装的控制台脚本；python -m 方式无入口）"""
    exe = shutil.which("mitmdump")
    if not exe:
        cand = Path(sys.executable).with_name("mitmdump.exe")
        exe = str(cand) if cand.exists() else "mitmdump"
    return [exe, "-q", "--listen-port", str(CAPTURE_PORT), "-s", str(ADDON_PATH)]


def _env() -> dict:
    env = dict(os.environ)
    env["REPORT_URL"] = f"http://{HOST}:{PORT}/report"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def start() -> subprocess.Popen:
    proc = subprocess.Popen(
        _mitmdump_cmd(),
        env=_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    return proc


def stop(proc: subprocess.Popen) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
