"""FastAPI 服务组装：REST + WebSocket + 静态前端"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import database
from .broadcaster import Broadcaster
from .capture import manager as capture_manager
from .config import APP_NAME, VERSION, RES_DIR, WEB_DIR, WS_PATH, REPORT_PATH
from .receiver import router as receiver_router

app = FastAPI(title=APP_NAME, version=VERSION)
app.state.broadcaster = Broadcaster()
app.state.capture_proc = None
database.init_db()

app.include_router(receiver_router)


@app.get("/api/health")
async def health():
    bc: Broadcaster = app.state.broadcaster
    return {
        "code": 0,
        "name": APP_NAME,
        "version": VERSION,
        "clients": bc.client_count,
        "buffered": len(bc.recent_snapshot()),
        "report_path": REPORT_PATH,
    }


@app.get("/api/entries")
async def entries(method: str = "", status: str = "", host: str = "",
                  search: str = "", level: str = "", limit: int = 100, offset: int = 0):
    rows, total = database.list_entries(
        method=method or None, status=status or None, host=host or None,
        search=search or None, level=level or None,
        limit=max(1, min(int(limit), 1000)), offset=max(0, int(offset)),
    )
    return {"code": 0, "total": total, "entries": rows}


@app.get("/api/entries/{entry_id}")
async def entry_detail(entry_id: int):
    row = database.get_entry(entry_id)
    if row is None:
        return {"code": 1, "msg": "not found"}
    return {"code": 0, "entry": row}


@app.get("/api/stats")
async def stats():
    return {"code": 0, **database.stats()}


@app.get("/api/feedback")
async def feedback(limit: int = 100):
    return {"code": 0, "items": database.recent_feedback(limit=max(1, min(int(limit), 500)))}


@app.post("/api/clear")
async def clear():
    n = database.clear_all()
    return {"code": 0, "cleared": n}


# ---------- 独立抓包模式 ----------
@app.post("/api/capture/start")
async def capture_start():
    proc = getattr(app.state, "capture_proc", None)
    if proc is not None and proc.poll() is None:
        return {"code": 0, "running": True, "port": capture_manager.CAPTURE_PORT,
                "cert": str(capture_manager.CA_CERT_PATH)}
    proc = capture_manager.start()
    app.state.capture_proc = proc
    return {"code": 0, "running": True, "port": capture_manager.CAPTURE_PORT,
            "cert": str(capture_manager.CA_CERT_PATH),
            "note": "把系统/WiFi代理指向 127.0.0.1:" + str(capture_manager.CAPTURE_PORT)}


@app.post("/api/capture/stop")
async def capture_stop():
    proc = getattr(app.state, "capture_proc", None)
    capture_manager.stop(proc)
    app.state.capture_proc = None
    return {"code": 0, "running": False}


@app.get("/api/capture/status")
async def capture_status():
    proc = getattr(app.state, "capture_proc", None)
    running = proc is not None and proc.poll() is None
    return {"code": 0, "running": running,
            "port": capture_manager.CAPTURE_PORT,
            "cert": str(capture_manager.CA_CERT_PATH)}


@app.websocket(WS_PATH)
async def ws_endpoint(websocket: WebSocket):
    bc: Broadcaster = app.state.broadcaster
    await websocket.accept()
    bc.connect(websocket)
    try:
        await websocket.send_json({
            "event": "init",
            "data": {"entries": bc.recent_snapshot(), "stats": database.stats()},
        })
        while True:
            await websocket.receive_json()  # 客户端心跳（pong）
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bc.disconnect(websocket)


# 静态资源：先挂 /res（图标），再挂 /（前端页面）
app.mount("/res", StaticFiles(directory=str(RES_DIR)), name="res")
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
