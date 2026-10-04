"""高岛的快递分拣站 —— 一键将 Python 脚本打包成 exe 的工具。"""

from pathlib import Path

__version__ = "0.1.0"

# 项目自身图标：用于窗口图标、任务栏图标，以及将来打包本工具时的 exe 图标
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ICON_PATH = str(_PROJECT_ROOT / "assets" / "app.ico")
