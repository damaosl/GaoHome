"""解包启动器：把任意文件打包进 exe 后，在运行时解包并用系统默认程序打开。

原理（来自 PyInstaller 官方运行时约定）：
- 打包时用 --add-data 把用户选择的文件放进 bundle；
- onefile 运行时 bootloader 会把 bundle 解包到临时目录，路径存于 sys._MEIPASS；
- 启动器从 sys._MEIPASS 读出载荷，复制到持久的临时目录后交给系统默认程序打开，
  避免 onefile 解包目录随进程退出被清理后文件失效。
"""
from __future__ import annotations

from pathlib import Path

# 启动器模板：{payload_name} 在打包前替换为用户选择的文件名（用 repr 保证安全）
LAUNCHER_TEMPLATE = '''"""由「高岛的快递分拣站」生成的解包启动器（请勿手动修改）。"""
import os
import shutil
import sys
import tempfile

PAYLOAD_NAME = {payload_name!r}


def _log(message: str) -> None:
    # --noconsole 模式下 sys.stdout 为 None，直接 print 会崩溃
    if sys.stdout is not None:
        print(message)


def main() -> int:
    # 打包运行时 bundle 解包目录（开发态回退到本文件所在目录）
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(base, PAYLOAD_NAME)

    if not os.path.exists(src):
        _log(f"未找到内置文件：{{PAYLOAD_NAME}}")
        return 1

    # 复制到持久的临时目录，避免 onefile 解包目录被清理后文件失效
    dst_dir = tempfile.mkdtemp(prefix="gaodao_")
    dst = os.path.join(dst_dir, PAYLOAD_NAME)
    try:
        shutil.copyfile(src, dst)
    except OSError as exc:
        _log(f"解包失败：{{exc}}")
        return 1

    # 交给系统默认程序打开（目标为 Windows）
    try:
        os.startfile(dst)
    except OSError as exc:
        _log(f"打开失败：{{exc}}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def render_launcher(payload_name: str) -> str:
    """把载荷文件名填入启动器模板，返回脚本源码。"""
    return LAUNCHER_TEMPLATE.format(payload_name=payload_name)


def write_launcher(payload_name: str, target_dir: str) -> str:
    """在 target_dir 下写入启动器脚本，返回脚本路径。"""
    path = Path(target_dir) / "launcher.py"
    path.write_text(render_launcher(payload_name), encoding="utf-8")
    return str(path)
