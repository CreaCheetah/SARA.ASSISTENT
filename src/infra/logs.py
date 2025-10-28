# src/infra/logs.py
import logging
import os
from datetime import datetime
from typing import Iterable, List, Dict, Any
from sqlalchemy import create_engine

# --- DB engine ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var ontbreekt")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=5,
)

# --- bootstrap: zorg dat tabel bestaat ---
DDL = """
CREATE TABLE IF NOT EXISTS logs (
  id     BIGSERIAL PRIMARY KEY,
  ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
  level  VARCHAR(10) NOT NULL,
  msg    TEXT NOT NULL
);
"""
with engine.begin() as conn:
    conn.exec_driver_sql(DDL)

# --- logging handler die naar DB schrijft ---
class DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.utcfromtimestamp(record.created)
            level = record.levelname
            msg = self.format(record)
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    "INSERT INTO logs (ts, level, msg) VALUES (%s, %s, %s)",
                    (ts, level, msg),
                )
        except Exception:  # geen logging-loop
            pass

def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # console voor Render logs
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        root.addHandler(sh)

    # database handler
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        dh = DBHandler()
        dh.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(dh)

# --- ophalen voor dashboard ---
def get_events(limit: int = 200, level: str | None = None, q: str | None = None) -> List[Dict[str, Any]]:
    sql = "SELECT ts, level, msg FROM logs"
    params: list[Any] = []
    where: list[str] = []

    if level and level.upper() in {"INFO", "WARN", "ERROR"}:
        where.append("level = %s")
        params.append(level.upper())

    if q:
        where.append("msg ILIKE %s")
        params.append(f"%{q}%")

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY id DESC LIMIT %s"
    params.append(int(limit))

    with engine.begin() as conn:
        rows = conn.exec_driver_sql(sql, tuple(params)).mappings().all()

    return [{"ts": r["ts"], "level": r["level"], "msg": r["msg"]} for r in rows]
