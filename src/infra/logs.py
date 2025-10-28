import json
import logging
from typing import Any, Dict, Iterable, List, Optional
from sqlalchemy import text
from .db import engine, init_db

# ---------- DB logging handler ----------

class DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        lvl = record.levelname
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO logs (level, msg) VALUES (:lvl, :msg)"),
                    {"lvl": lvl, "msg": msg},
                )
        except Exception:
            # Val stil als DB hikt
            pass

def setup_logging() -> None:
    init_db()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # console
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(logging.StreamHandler())
    # db
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        dbh = DBHandler()
        dbh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        root.addHandler(dbh)

# ---------- Queries voor dashboard ----------

def get_events(limit: int = 300, level: Optional[str] = None, q: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT ts, level, msg FROM logs"
    conds: List[str] = []
    params: Dict[str, Any] = {}
    if level in ("INFO", "WARN", "ERROR"):
        conds.append("level = :lvl")
        params["lvl"] = level
    if q:
        conds.append("msg ILIKE :q")
        params["q"] = f"%{q}%"
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC"
    sql += f" LIMIT {int(limit)}"  # geen bindparam in LIMIT i.v.m. psycopg2
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]

# ---------- Call-logging helpers ----------

def _jsonable(data: Any) -> Optional[str]:
    if data is None:
        return None
    try:
        return json.dumps(data)
    except Exception:
        return json.dumps({"_repr": str(data)})

def mask_number(nr: Optional[str]) -> Optional[str]:
    if not nr:
        return None
    s = nr.strip()
    return s[:-6] + "******" + s[-2:] if len(s) > 8 else "****"

def log_call_start(call_id: str, from_nr: Optional[str], to_nr: Optional[str]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO call_sessions (call_id, from_masked, to_number)
            VALUES (:cid, :frm, :to)
            ON CONFLICT (call_id) DO NOTHING
            """),
            {"cid": call_id, "frm": mask_number(from_nr), "to": to_nr},
        )
        conn.execute(
            text("""
            INSERT INTO call_events (call_id, event, level)
            VALUES (:cid, 'call_start', 'INFO')
            """),
            {"cid": call_id},
        )

def log_call_event(call_id: str, event: str, level: str = "INFO",
                   data: Any = None, latency_ms: Optional[int] = None,
                   status_code: Optional[int] = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO call_events
                (call_id, event, level, data_json, latency_ms, status_code)
            VALUES
                (:cid, :evt, :lvl, CAST(:data AS JSONB), :lat, :code)
            """),
            {
                "cid": call_id,
                "evt": event,
                "lvl": level,
                "data": _jsonable(data),
                "lat": latency_ms,
                "code": status_code,
            },
        )

def log_call_end(call_id: str, duration_sec: Optional[int], result: str,
                 error_code: Optional[str] = None, error_msg: Optional[str] = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
            UPDATE call_sessions
               SET ended_at = now(),
                   duration_sec = COALESCE(:dur, duration_sec),
                   result = :res,
                   error_code = :ecode,
                   error_msg = :emsg
             WHERE call_id = :cid
            """),
            {"cid": call_id, "dur": duration_sec, "res": result,
             "ecode": error_code, "emsg": error_msg},
        )
        conn.execute(
            text("""
            INSERT INTO call_events (call_id, event, level, data_json)
            VALUES (:cid, 'call_end', CASE WHEN :res = 'ok' THEN 'INFO' ELSE 'ERROR' END,
                    jsonb_build_object('result', :res))
            """),
            {"cid": call_id, "res": result},
        )
