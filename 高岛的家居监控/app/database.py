"""SQLite 持久化：落库、查询、统计"""
import json
import sqlite3
import threading
from datetime import datetime

from .config import DATA_DIR, DB_PATH, HISTORY_LIMIT

_lock = threading.RLock()  # 可重入：save() 持锁时 _ensure_init→init_db 可再次进入
_initialized = False

_COLUMNS = (
    "timestamp, method, scheme, host, url, path, query, status, status_text, "
    "http_version, content_type, duration_ms, size_request, size_response, "
    "server_ip, client_ip, platform, rule, level, feedback, "
    "request_headers, response_headers, request_body, response_body, body_encoding"
)


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _lock:
        c = _conn()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                timestamp TEXT, method TEXT, scheme TEXT, host TEXT, url TEXT,
                path TEXT, query TEXT, status INTEGER, status_text TEXT,
                http_version TEXT, content_type TEXT, duration_ms REAL,
                size_request INTEGER, size_response INTEGER,
                server_ip TEXT, client_ip TEXT, platform TEXT, rule TEXT,
                level TEXT, feedback TEXT,
                request_headers TEXT, response_headers TEXT,
                request_body TEXT, response_body TEXT, body_encoding TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_entries_host ON entries(host);
            CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);
            CREATE INDEX IF NOT EXISTS idx_entries_level ON entries(level);
            CREATE INDEX IF NOT EXISTS idx_entries_id ON entries(id);
            """
        )
        c.commit()
        c.close()


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("feedback", "request_headers", "response_headers"):
        try:
            d[key] = json.loads(d.get(key) or ("[]" if key == "feedback" else "{}"))
        except Exception:
            d[key] = [] if key == "feedback" else {}
    return d


def _ensure_init() -> None:
    """惰性建表：任何公共函数首次调用时保证表结构存在"""
    global _initialized
    if _initialized:
        return
    init_db()
    _initialized = True


def save(entry: dict) -> int:
    """落库并返回自增 id；按 HISTORY_LIMIT 裁剪旧数据"""
    with _lock:
        _ensure_init()
        c = _conn()
        cur = c.execute(
            f"INSERT INTO entries({_COLUMNS}) VALUES("
            + ",".join("?" * len(_COLUMNS.split(","))) + ")",
            (
                entry.get("timestamp", ""),
                entry.get("method", ""),
                entry.get("scheme", ""),
                entry.get("host", ""),
                entry.get("url", ""),
                entry.get("path", ""),
                entry.get("query", ""),
                entry.get("status", 0),
                entry.get("status_text", ""),
                entry.get("http_version", ""),
                entry.get("content_type", ""),
                entry.get("duration_ms", 0),
                entry.get("size_request", 0),
                entry.get("size_response", 0),
                entry.get("server_ip", ""),
                entry.get("client_ip", ""),
                entry.get("platform", ""),
                entry.get("rule", ""),
                entry.get("level", "info"),
                json.dumps(entry.get("feedback") or [], ensure_ascii=False),
                json.dumps(entry.get("request_headers") or {}, ensure_ascii=False),
                json.dumps(entry.get("response_headers") or {}, ensure_ascii=False),
                entry.get("request_body", ""),
                entry.get("response_body", ""),
                entry.get("body_encoding", ""),
            ),
        )
        rid = cur.lastrowid
        if HISTORY_LIMIT > 0:
            c.execute(
                "DELETE FROM entries WHERE id NOT IN "
                "(SELECT id FROM entries ORDER BY id DESC LIMIT ?)",
                (HISTORY_LIMIT,),
            )
        c.commit()
        c.close()
        return rid


def list_entries(method=None, status=None, host=None, search=None, level=None,
                 limit=100, offset=0) -> list:
    where, args = [], []
    if method:
        where.append("method = ?")
        args.append(method.upper())
    if status:
        try:
            s = int(status)
            if 100 <= s <= 599:
                where.append("status = ?")
                args.append(s)
            elif 1 <= s <= 5:  # 状态类：4 -> 4xx
                where.append("status >= ? AND status < ?")
                args.extend([s * 100, (s + 1) * 100])
        except (TypeError, ValueError):
            pass
    if host:
        where.append("host LIKE ?")
        args.append(f"%{host}%")
    if level:
        where.append("level = ?")
        args.append(level)
    if search:
        where.append("(url LIKE ? OR host LIKE ? OR response_body LIKE ? OR request_body LIKE ?)")
        args.extend([f"%{search}%"] * 4)
    sql = "SELECT * FROM entries" + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    args.extend([int(limit), int(offset)])
    with _lock:
        _ensure_init()
        c = _conn()
        rows = c.execute(sql, args).fetchall()
        total = c.execute(
            "SELECT COUNT(*) AS n FROM entries"
            + (" WHERE " + " AND ".join(where) if where else ""),
            args[:-2],
        ).fetchone()["n"]
        c.close()
    return [_row_to_dict(r) for r in rows], total


def get_entry(entry_id: int):
    with _lock:
        _ensure_init()
        c = _conn()
        row = c.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        c.close()
    return _row_to_dict(row) if row else None


def stats() -> dict:
    """看板概览统计"""
    with _lock:
        _ensure_init()
        c = _conn()
        row = c.execute(
            "SELECT COUNT(*) n, "
            "SUM(CASE WHEN status>=400 THEN 1 ELSE 0 END) errors, "
            "SUM(CASE WHEN level='alert' THEN 1 ELSE 0 END) alerts, "
            "SUM(CASE WHEN level='warn' THEN 1 ELSE 0 END) warns, "
            "SUM(size_response) traffic, AVG(duration_ms) avg_ms "
            "FROM entries"
        ).fetchone()
        domains = c.execute(
            "SELECT host, COUNT(*) n FROM entries WHERE host != '' "
            "GROUP BY host ORDER BY n DESC LIMIT 10"
        ).fetchall()
        statuses = c.execute(
            "SELECT status, COUNT(*) n FROM entries WHERE status > 0 "
            "GROUP BY status ORDER BY n DESC LIMIT 10"
        ).fetchall()
        c.close()
    return {
        "total": row["n"] or 0,
        "errors": row["errors"] or 0,
        "alerts": row["alerts"] or 0,
        "warns": row["warns"] or 0,
        "traffic": row["traffic"] or 0,
        "avg_ms": round(row["avg_ms"] or 0, 1),
        "top_domains": [{"host": d["host"], "count": d["n"]} for d in domains],
        "top_status": [{"status": s["status"], "count": s["n"]} for s in statuses],
    }


def recent_feedback(limit=100) -> list:
    """最近的反馈（供反馈面板）"""
    with _lock:
        _ensure_init()
        c = _conn()
        rows = c.execute(
            "SELECT id, created_at, host, url, method, status, level, feedback "
            "FROM entries WHERE feedback NOT IN ('[]','null','') "
            "ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        c.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["feedback"] = json.loads(d["feedback"] or "[]")
        except Exception:
            d["feedback"] = []
        out.append(d)
    return out


def clear_all() -> int:
    """清空抓包数据（仅数据库记录）"""
    with _lock:
        _ensure_init()
        c = _conn()
        cur = c.execute("DELETE FROM entries")
        n = cur.rowcount
        c.commit()
        c.close()
    return n
