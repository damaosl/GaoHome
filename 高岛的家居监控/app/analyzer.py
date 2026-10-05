"""分析反馈引擎 —— 对每条抓包数据实时检测并给出反馈（协同小黄鸟工作）。

规则一览：
  1. 5xx / 4xx / 401 / 403 / 无响应         —— 状态异常
  2. 慢响应（> SLOW_MS）                    —— 性能
  3. 大体积响应（> BIG_BODY）               —— 性能
  4. 明文 HTTP（非内网地址）                —— 安全
  5. 凭证出现在 URL / 响应含敏感字段 / Cookie 不安全 —— 安全
  6. 错误风暴（同主机短窗口多次 5xx）       —— 稳定性

输出：就地修改 entry 的 level（info/warn/alert）与 feedback 列表。
"""
import re
import time as _time
from collections import defaultdict, deque

from .config import SLOW_MS, BIG_BODY, ERROR_BURST, BURST_WINDOW_SEC
from .models import LEVEL_INFO, LEVEL_WARN, LEVEL_ALERT

# 同主机错误时间戳窗口（错误风暴检测）
_burst: dict = defaultdict(deque)

_SENSITIVE_KEYS = re.compile(
    r'"(password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key|'
    r'private[_-]?key|client[_-]?secret)"\s*:', re.IGNORECASE
)
_URL_CREDENTIALS = re.compile(r"[?&](password|passwd|pwd|token|apikey|api_key|secret)=", re.IGNORECASE)
_PRIVATE_HOST = re.compile(
    r"^(localhost|127\.|10\.|192\.168\.|0\.0\.0\.0|\[::1\]|172\.(1[6-9]|2\d|3[01])\.|.+\.local$)",
    re.IGNORECASE,
)


def analyze(entry: dict) -> None:
    entry.setdefault("level", LEVEL_INFO)
    entry.setdefault("feedback", [])

    status = entry.get("status") or 0
    host = entry.get("host") or ""
    scheme = (entry.get("scheme") or "").lower()
    duration = float(entry.get("duration_ms") or 0)
    size_res = int(entry.get("size_response") or 0)

    # ---- 1. 状态异常 ----
    if 500 <= status <= 599:
        _mark(entry, LEVEL_ALERT, f"服务器错误 {status}",
              "目标服务端返回 5xx，建议检查服务端日志与运行状态。")
        _check_burst(entry, host)
    elif status in (401, 403):
        _mark(entry, LEVEL_WARN, f"鉴权失败 {status}",
              "请求被拒绝（401/403），请检查 Token、Cookie 或登录状态是否有效。")
    elif 400 <= status <= 499:
        _mark(entry, LEVEL_WARN, f"客户端错误 {status}",
              "请求被服务端拒绝（4xx），请检查请求参数、格式或接口地址。")
    elif status == 0:
        _mark(entry, LEVEL_WARN, "无响应状态",
              "未取得响应状态码，可能是连接失败或会话被中断。")

    # ---- 2. 慢响应 ----
    if duration > SLOW_MS:
        _mark(entry, LEVEL_WARN, f"响应缓慢 {duration:.0f} ms",
              f"耗时超过 {SLOW_MS} ms，请检查接口性能、网络链路或后端负载。")

    # ---- 3. 大体积响应 ----
    if size_res > BIG_BODY:
        _mark(entry, LEVEL_WARN, f"大体积响应 {size_res / 1048576:.1f} MB",
              "响应体超过 1MB，建议启用压缩、分页或按需加载。")

    # ---- 4. 明文 HTTP（外网） ----
    if scheme == "http" and host and not _PRIVATE_HOST.match(host):
        _mark(entry, LEVEL_WARN, "明文 HTTP 传输",
              "未加密传输，内容可能被窃听或篡改，建议尽快升级 HTTPS。")

    # ---- 5. 敏感数据 ----
    if _URL_CREDENTIALS.search(entry.get("url") or ""):
        _mark(entry, LEVEL_ALERT, "凭证出现在 URL 中",
              "密码 / Token 等敏感信息放在 URL 里会被记录到日志与历史记录，请改用请求体或请求头。")
    if _SENSITIVE_KEYS.search(entry.get("response_body") or ""):
        _mark(entry, LEVEL_WARN, "响应包含敏感字段",
              "响应体中出现 password / token / secret 等字段，请确认是否属于业务预期。")
    _check_cookies(entry)


def _check_burst(entry: dict, host: str) -> None:
    """错误风暴：同一主机在短窗口内多次 5xx"""
    if not host:
        return
    now = _time.time()
    q = _burst[host]
    while q and q[0] < now - BURST_WINDOW_SEC:
        q.popleft()
    q.append(now)
    if len(q) >= ERROR_BURST:
        _mark(entry, LEVEL_ALERT, f"错误风暴：{host}",
              f"近 {BURST_WINDOW_SEC}s 内该主机已出现 {len(q)} 次 5xx 错误，"
              "建议立即排查服务端稳定性或依赖服务。")


def _check_cookies(entry: dict) -> None:
    sc = (entry.get("response_headers") or {}).get("set-cookie", "")
    if not sc:
        return
    low = sc.lower()
    if "httponly" not in low:
        _mark(entry, LEVEL_WARN, "Cookie 缺少 HttpOnly",
              "Set-Cookie 未设置 HttpOnly，XSS 脚本可能窃取该 Cookie。")
    scheme = (entry.get("scheme") or "").lower()
    if scheme == "https" and "secure" not in low:
        _mark(entry, LEVEL_WARN, "Cookie 缺少 Secure",
              "HTTPS 站点下 Cookie 未设置 Secure，存在被降级攻击截获的风险。")


def _mark(entry: dict, level: str, title: str, detail: str) -> None:
    entry["feedback"].append({"level": level, "title": title, "detail": detail})
    rank = {LEVEL_INFO: 0, LEVEL_WARN: 1, LEVEL_ALERT: 2}
    if rank.get(level, 0) > rank.get(entry.get("level", LEVEL_INFO), 0):
        entry["level"] = level
