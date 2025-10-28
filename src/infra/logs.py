import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from .db import engine

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
  id SERIAL PRIMARY KEY,
  ts TEXT NOT NULL,
  level TEXT NOT NULL,
  msg TEXT NOT NULL
);
"""

INSERT_SQL = text("INSERT INTO logs (ts, level, msg) VALUES (:ts, :level, :msg)")
SELECT_BASE = "SELECT id, ts, level, msg FROM logs"
DELETE_OLD  = text("DELETE FROM logs WHERE id < (SELECT COALESCE(MAX(id),0) - :keep FROM logs)")

class DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            lvl = record.levelname
            ts  = getattr(record, "asctime", None)
            if ts is None:
                from datetime import datetime
                ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            with engine.begin() as conn:
                conn.execute(INSERT_SQL, {"ts": ts, "level": lvl, "msg": msg})
                conn.execute(DELETE_OLD, {"keep": 5000})
        except Exception:  # geen re-raise in logging
            pass

def setup_logging() -> None:
    # tabel garanderen
    with engine.begin() as conn:
        conn.exec_driver_sql(TABLE_SQL)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # nette formatter (zelfde in console en DB)
    fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
    for h in root.handlers:
        try:
            h.setFormatter(fmt)
        except Exception:
            pass

    # voeg DB-handler toe als die er nog niet is
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        dbh = DBHandler()
        dbh.setLevel(logging.INFO)
        dbh.setFormatter(fmt)
        root.addHandler(dbh)

def get_events(limit: int = 200, level: Optional[str] = None, q: Optional[str] = None) -> List[Dict[str, Any]]:
    where = []
    params: Dict[str, Any] = {}
    if level:
        where.append("level = :level")
        params["level"] = level.upper()
    if q:
        where.append("msg ILIKE :q")
        params["q"] = f"%{q}%"

    sql = SELECT_BASE
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT :limit"
    params["limit"] = max(1, min(limit, 1000))

    with engine.begin() as conn:
        rows = conn.exec_driver_sql(sql, params).mappings().all()
    return [dict(r) for r in rows]
