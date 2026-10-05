"""内部数据模型（抓包条目）"""
from dataclasses import dataclass, field, asdict

LEVEL_INFO = "info"
LEVEL_WARN = "warn"
LEVEL_ALERT = "alert"


@dataclass
class Entry:
    """一条规范化后的抓包记录（HAR → Entry）"""
    id: int = 0                       # 数据库自增 id
    timestamp: str = ""               # 发起时间（Reqable 提供）
    method: str = ""
    scheme: str = ""                  # http / https
    host: str = ""                    # 域名:端口
    url: str = ""                     # 完整 URL
    path: str = ""                    # 路径（含参数）
    query: str = ""
    status: int = 0
    status_text: str = ""
    http_version: str = ""
    content_type: str = ""
    duration_ms: float = 0.0
    size_request: int = 0             # 请求体大小（字节）
    size_response: int = 0            # 响应体大小（字节）
    server_ip: str = ""
    client_ip: str = ""
    platform: str = ""                # x-reqable-platform：抓包来源平台
    rule: str = ""                    # x-reqable-reporter-rule：命中的上报规则
    request_headers: dict = field(default_factory=dict)
    response_headers: dict = field(default_factory=dict)
    request_body: str = ""
    response_body: str = ""
    body_encoding: str = ""           # 响应体编码提示（如 base64）
    level: str = LEVEL_INFO           # info / warn / alert
    feedback: list = field(default_factory=list)  # 分析反馈列表

    def to_dict(self) -> dict:
        return asdict(self)
