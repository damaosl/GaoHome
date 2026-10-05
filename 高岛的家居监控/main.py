"""入口：一键启动「高岛的家居监控」

用法：
    python main.py                     # 默认：桌面窗口（pywebview + app.ico）
    python main.py --mode browser      # 用系统浏览器打开看板
    python main.py --mode server       # 仅后台服务，不开窗口
    python main.py --port 8091         # 自定义端口
"""
import argparse
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from app.config import APP_NAME, VERSION, HOST, PORT, ICON_PATH, REPORT_PATH, DATA_DIR
from app.server import app


def _log(msg: str) -> None:
    """启动日志（pythonw 无控制台时便于排查）"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "startup.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _wait_ready(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def run_server(host: str, port: int) -> None:
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except Exception:
        _log("run_server 异常: " + traceback.format_exc())


def _hold() -> None:
    while True:
        time.sleep(3600)


def _port_in_use(host: str, port: int) -> bool:
    """检测端口是否已被占用（已有实例在跑则复用）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
    except OSError:
        return True


def main() -> None:
    try:
        _main()
    except Exception:
        _log("FATAL: " + traceback.format_exc())
        raise


def _main() -> None:
    # pythonw（无控制台）下 sys.stdout/stderr 为 None，uvicorn 日志会崩溃，先重定向
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        sys.stderr = open(DATA_DIR / "server.log", "a", encoding="utf-8")

    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--mode", choices=["window", "browser", "server"], default="window")
    args = ap.parse_args()
    _log(f"启动 {APP_NAME} v{VERSION} mode={args.mode} host={args.host} port={args.port}")

    url = f"http://{args.host}:{args.port}/"
    report_url = url.rstrip("/") + REPORT_PATH

    if _port_in_use(args.host, args.port):
        _log(f"端口 {args.port} 已被占用 → 复用已有实例")
        # 已有实例在运行：不再重复启动服务，直接复用
        if args.mode == "server":
            print(f"端口 {args.port} 已被占用，服务可能已在运行: {url}")
            _hold()
        if args.mode == "browser":
            webbrowser.open(url)
            print(f"[{APP_NAME}] 检测到已有实例，已用浏览器打开 {url}")
            _hold()
        print(f"[{APP_NAME}] 检测到已有实例，直接打开窗口: {url}")
        _run_window(url, reuse=True)
        return

    t = threading.Thread(target=run_server, args=(args.host, args.port), daemon=True)
    t.start()
    _log("服务线程已启动")

    if args.mode == "server":
        print(f"[{APP_NAME} v{VERSION}] 服务已启动")
        print(f"  看板:     {url}")
        print(f"  上报接口: {report_url}（在 Reqable 报告服务器中填此地址）")
        _hold()

    if not _wait_ready(url):
        _log("服务启动失败（等待超时）")
        print("服务启动失败，请检查端口是否被占用。")
        sys.exit(1)
    _log("服务就绪: " + url)

    if args.mode == "browser":
        webbrowser.open(url)
        print(f"[{APP_NAME} v{VERSION}] 已用浏览器打开 {url}")
        _hold()

    # ---- 桌面窗口模式 ----
    _run_window(url)


def _run_window(url: str, reuse: bool = False) -> None:
    """打开桌面窗口；窗口关闭后进程退出"""
    _log("创建窗口: " + url + (" (复用)" if reuse else ""))
    try:
        import webview
    except ImportError:
        print("pywebview 未安装，改用浏览器打开。")
        webbrowser.open(url)
        _hold()

    try:
        webview.create_window(
            APP_NAME, url,
            width=1280, height=800, min_size=(960, 600),
        )
        if reuse:
            print(f"[{APP_NAME}] 复用已有服务实例（窗口关闭不影响后台服务）")
        else:
            print(f"[{APP_NAME} v{VERSION}] 桌面窗口已启动（图标: {ICON_PATH.name if ICON_PATH.exists() else '未找到'}）")
        # pywebview 6.x：窗口图标通过 start(icon=...) 传入
        webview.start(icon=str(ICON_PATH) if ICON_PATH.exists() else None)
        _log("窗口已关闭，进程退出")
    except Exception:
        _log("窗口创建失败: " + traceback.format_exc())
        print("窗口创建失败，改用浏览器打开。")
        webbrowser.open(url)
        _hold()
    sys.exit(0)  # 窗口关闭 → 程序退出


if __name__ == "__main__":
    main()
