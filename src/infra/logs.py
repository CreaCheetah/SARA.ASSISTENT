import json
import logging
from sqlalchemy import text
from .db import engine, init_db

# ---- basis logging naar tabel 'logs' ----
class DBHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        lvl = record.levelname
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO logs (level, msg) VALUES (:level, :msg)"),
                {"level": lvl, "msg": msg},
            )

def setup_logging():
    init_db()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # dubbelhandlers voorkomen
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        h = DBHandler()
        f = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        h.setFormatter(f)
        root.addHandler(h)

# ---- opvragen voor dashboard ----
def get_events(limit=300, level=None, q=None):
    where = []
    params = {}
    if level:
        where.append("level = :level")
        params["level"] = level
    if q:
        where.append("msg ILIKE :q")
        params["q"] = f"%{q}%"
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT ts, level, msg FROM logs {where_sql} ORDER BY id DESC LIMIT :lim"
    params["lim"] = int(limit)
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    # lijst van dicts terug
    return rows

# ---- call logging helpers ----
def start_call(call_id: str, from_masked: str, to_number: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO call_sessions (call_id, from_masked, to_number)
                VALUES (:cid, :frm, :to)
                ON CONFLICT (call_id) DO NOTHING
            """),
            {"cid": call_id, "frm": from_masked, "to": to_number},
        )

def end_call(call_id: str, result: str | None = None,
             error_code: str | None = None, error_msg: str | None = None):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE call_sessions
                   SET ended_at = now(),
                       duration_sec = COALESCE(EXTRACT(EPOCH FROM (now()-started_at))::int, duration_sec),
                       result = COALESCE(:res, result),
                       error_code = :ecode,
                       error_msg  = :emsg
                 WHERE call_id = :cid
            """),
            {"cid": call_id, "res": result, "ecode": error_code, "emsg": error_msg},
        )

def log_call_event(call_id: str, event: str, level: str = "INFO",
                   data: dict | None = None, latency_ms: int | None = None,
                   status_code: int | None = None):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO call_events (call_id, event, level, data_json, latency_ms, status_code)
                VALUES (:cid, :evt, :lvl, CAST(:data AS JSONB), :lat, :code)
            """),
            {
                "cid": call_id,
                "evt": event,
                "lvl": level,
                "data": json.dumps(data) if data is not None else None,
                "lat": latency_ms,
                "code": status_code,
            },
        )
