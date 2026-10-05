"""HAR 解析器：把 Reqable 上报的 HAR 组织格式规范化成内部字典。

兼容三种输入形状：
1. 完整 HAR 日志：{"log": {"entries": [...]}}
2. 单个条目：{"request": ..., "response": ...}
3. 条目数组：[{...}, {...}]
"""
import base64
import json
from urllib.parse import urlsplit

from .config import BODY_LIMIT


def _headers_to_dict(headers) -> dict:
    """[{"name": k, "value": v}, ...] -> {小写名: 合并值}"""
    if not headers:
        return {}
    out = {}
    for h in headers:
        if isinstance(h, dict) and "name" in h:
            name = str(h.get("name", "")).lower()
            if not name:
                continue
            value = str(h.get("value", ""))
            if name in out:
                out[name] += ", " + value
            else:
                out[name] = value
    return out


def _decode_content(content):
    """HAR 的 response.content：可能带 base64 编码"""
    text = ""
    encoding = ""
    if isinstance(content, dict):
        text = content.get("text") or ""
        encoding = content.get("encoding") or ""
    elif isinstance(content, str):
        text = content
    if encoding == "base64" and text:
        try:
            text = base64.b64decode(text).decode("utf-8", errors="replace")
            encoding = ""  # 已还原，清除标记
        except Exception:
            pass
    return text, encoding


def _truncate(s: str, limit: int = BODY_LIMIT) -> str:
    if isinstance(s, str) and len(s) > limit:
        return s[:limit] + "\n…[已截断]"
    return s or ""


def _extract_request_body(req: dict) -> str:
    pd = req.get("postData")
    if isinstance(pd, dict):
        text = pd.get("text") or ""
        if text:
            return _truncate(text)
        params = pd.get("params")
        if isinstance(params, list) and params:
            try:
                return _truncate(json.dumps(params, ensure_ascii=False, indent=2))
            except Exception:
                return ""
    return ""


def _parse_entry(e: dict):
    """单条 HAR entry -> 内部字段字典；无法解析时返回 None"""
    try:
        req = e.get("request") or {}
        resp = e.get("response") or {}
        url = req.get("url", "")
        parts = urlsplit(url)

        resp_body, resp_enc = _decode_content(resp.get("content"))
        content = resp.get("content")
        size_res = content.get("size") if isinstance(content, dict) else None
        if not size_res:
            size_res = resp.get("bodySize") or len(resp_body.encode("utf-8", "ignore")) or 0
        size_req = req.get("bodySize") or len(_extract_request_body(req).encode("utf-8", "ignore")) or 0

        headers_rs = _headers_to_dict(resp.get("headers"))

        return dict(
            timestamp=e.get("startedDateTime") or "",
            method=(req.get("method") or "").upper(),
            scheme=parts.scheme or "",
            host=parts.netloc or "",
            url=url,
            path=parts.path or "/",
            query=parts.query or "",
            status=int(resp.get("status") or 0),
            status_text=resp.get("statusText") or "",
            http_version=resp.get("httpVersion") or req.get("httpVersion") or "",
            content_type=headers_rs.get("content-type", ""),
            duration_ms=float(e.get("time") or 0),
            size_request=int(size_req or 0),
            size_response=int(size_res or 0),
            server_ip=e.get("serverIPAddress") or "",
            client_ip=e.get("clientIPAddress") or "",
            request_headers=_headers_to_dict(req.get("headers")),
            response_headers=headers_rs,
            request_body=_extract_request_body(req),
            response_body=_truncate(resp_body),
            body_encoding=resp_enc,
            level="info",
            feedback=[],
        )
    except Exception:
        return None


def parse_har_body(body) -> list:
    """解析任意 HAR 形状，返回内部字段字典列表"""
    entries = []
    if isinstance(body, dict):
        log = body.get("log")
        if isinstance(log, dict):
            entries = log.get("entries") or []
        elif "request" in body or "response" in body:
            entries = [body]
        elif isinstance(body.get("entries"), list):
            entries = body["entries"]
    elif isinstance(body, list):
        entries = body

    out = []
    for e in entries:
        if isinstance(e, dict):
            parsed = _parse_entry(e)
            if parsed:
                out.append(parsed)
    return out
