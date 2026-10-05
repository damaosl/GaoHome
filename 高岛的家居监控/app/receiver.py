"""联动接收核心：Reqable 上报服务器（小黄鸟联动）的接收路由。

Reqable 每完成一个会话，会把数据按 HAR 组织格式 POST 到本服务。
支持 gzip / br / zstd 三种压缩（Content-Encoding）。
附带头：x-reqable-platform / x-reqable-reporter-host / x-reqable-reporter-rule
"""
import gzip
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import database
from .analyzer import analyze
from .config import REPORT_PATH
from .har_parser import parse_har_body

router = APIRouter()


async def _read_raw(request: Request) -> bytes:
    raw = await request.body()
    enc = (request.headers.get("content-encoding") or "").lower()
    if not raw or not enc:
        return raw
    try:
        if "br" in enc:
            import brotli
            return brotli.decompress(raw)
        if "zstd" in enc:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(raw)
        if "gzip" in enc:
            return gzip.decompress(raw)
    except Exception:
        pass
    return raw


@router.post(REPORT_PATH)
async def receive_report(request: Request):
    """接收小黄鸟（Reqable）上报的抓包数据"""
    raw = await _read_raw(request)
    try:
        body = json.loads(raw or b"{}")
    except Exception:
        return JSONResponse({"code": 1, "msg": "请求体不是合法 JSON"}, status_code=400)

    platform = request.headers.get("x-reqable-platform", "")
    rule = request.headers.get("x-reqable-reporter-rule", "")
    reporter_host = request.headers.get("x-reqable-reporter-host", "")

    items = parse_har_body(body)
    broadcaster = request.app.state.broadcaster
    received = 0
    for item in items:
        if not item.get("host") and reporter_host:
            item["host"] = reporter_host
        item["platform"] = item.get("platform") or platform
        item["rule"] = rule
        analyze(item)                       # 实时检测 + 反馈
        rid = database.save(item)           # 落库
        item["id"] = rid
        await broadcaster.push("entry", item)  # 实时推送到看板
        received += 1

    return {"code": 0, "msg": "ok", "received": received}
