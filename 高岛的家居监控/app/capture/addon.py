"""mitmproxy 抓包插件（独立抓包模式）

把每个完成的会话转成 HAR 组织格式，POST 给本工具的上报接口 /report，
与 Reqable（小黄鸟）上报走完全相同的解析 / 分析 / 展示链路。

REPORT_URL 环境变量由 manager 注入，默认指向本机 8090。
用法（由 manager 以子进程方式启动）：
    mitmdump -q --listen-port 8888 -s addon.py
"""
import base64
import json
import os
import urllib.request
from datetime import datetime, timezone

from mitmproxy import http

REPORT_URL = os.environ.get("REPORT_URL", "http://127.0.0.1:8090/report")


def _headers_dict(headers) -> list:
    return [{"name": k, "value": v} for k, v in headers.items()]


def _safe_text(msg):
    """取文本内容；二进制则转 base64 并标记编码"""
    try:
        return msg.get_text(strict=True) or "", ""
    except ValueError:
        raw = msg.raw_content or b""
        if not raw:
            return "", ""
        return base64.b64encode(raw).decode("ascii"), "base64"


def response(flow: http.HTTPFlow) -> None:
    req, resp = flow.request, flow.response
    if resp is None:
        return

    req_text, _ = _safe_text(req)
    resp_text, resp_enc = _safe_text(resp)

    ts_start = getattr(flow, "timestamp_start", None) or 0
    ts_end = getattr(flow, "timestamp_end", None) or 0
    started = ""
    if ts_start:
        try:
            started = datetime.fromtimestamp(ts_start, tz=timezone.utc).isoformat()
        except Exception:
            pass

    server_ip = ""
    if flow.server_conn and flow.server_conn.address:
        server_ip = flow.server_conn.address[0] or ""
    client_ip = ""
    if flow.client_conn and flow.client_conn.address:
        client_ip = flow.client_conn.address[0] or ""

    entry = {
        "startedDateTime": started,
        "time": round(max(ts_end - ts_start, 0) * 1000, 1),
        "request": {
            "method": req.method,
            "url": req.pretty_url,
            "httpVersion": req.http_version,
            "headers": _headers_dict(req.headers),
            "queryString": [{"name": k, "value": v} for k, v in req.query.items()],
            "bodySize": len(req.raw_content or b""),
            "postData": {
                "mimeType": req.headers.get("content-type", ""),
                "text": req_text,
            } if (req.raw_content or b"") else None,
        },
        "response": {
            "status": resp.status_code,
            "statusText": resp.reason,
            "httpVersion": resp.http_version,
            "headers": _headers_dict(resp.headers),
            "content": {
                "size": len(resp.raw_content or b""),
                "mimeType": resp.headers.get("content-type", ""),
                "text": resp_text,
                "encoding": resp_enc,
            },
        },
        "serverIPAddress": server_ip,
        "clientIPAddress": client_ip,
    }

    data = json.dumps({"log": {"entries": [entry]}}, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        REPORT_URL, data=data,
        headers={
            "Content-Type": "application/json",
            "x-reqable-platform": "capture",
            "x-reqable-reporter-rule": "builtin-proxy",
        },
    )
    try:
        urllib.request.urlopen(r, timeout=2)
    except Exception:
        pass  # 上报失败不影响抓包本身
