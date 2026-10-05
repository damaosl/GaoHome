"""WebSocket 广播器 + 内存回放缓冲"""
from collections import deque

from .config import RECENT_LIMIT


class Broadcaster:
    """维护所有看板连接，把新条目实时推给每个前端"""

    def __init__(self):
        self.clients: set = set()
        self.recent: deque = deque(maxlen=RECENT_LIMIT)

    def connect(self, ws) -> None:
        self.clients.add(ws)

    def disconnect(self, ws) -> None:
        self.clients.discard(ws)

    async def push(self, event: str, data) -> None:
        """广播事件；entry 事件同时写入回放缓冲"""
        if event == "entry":
            self.recent.append(data)
        message = {"event": event, "data": data}
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def recent_snapshot(self) -> list:
        return list(self.recent)

    @property
    def client_count(self) -> int:
        return len(self.clients)
