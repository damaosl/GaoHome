"""全局配置 —— 高岛的家居监控"""
from pathlib import Path

APP_NAME = "高岛的家居监控"
VERSION = "0.1.0"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"          # 极简前端
RES_DIR = BASE_DIR / "res"          # 图标等资源
DATA_DIR = BASE_DIR / "data"        # 数据库目录
DB_PATH = DATA_DIR / "capture.db"
ICON_PATH = RES_DIR / "app.ico"

# 服务监听（Reqable 上报服务器指向这里）
HOST = "127.0.0.1"
PORT = 8090
REPORT_PATH = "/report"             # Reqable 配置的接收路径
WS_PATH = "/ws"                     # 前端实时推送

# 内存回放缓冲：新打开的看板立即看到最近 N 条
RECENT_LIMIT = 500
# 单条记录请求/响应体落库上限（字节）
BODY_LIMIT = 256 * 1024
# 数据库保留的历史条数（0 = 不限制）
HISTORY_LIMIT = 20000

# 分析反馈引擎参数
SLOW_MS = 3000                      # 超过该毫秒数视为慢响应
BIG_BODY = 1024 * 1024              # 超过该字节数视为大包
ERROR_BURST = 5                     # 同一主机短窗口内错误次数达到即告警
BURST_WINDOW_SEC = 60
