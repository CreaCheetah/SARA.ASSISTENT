# src/infra/logs.py
import logging
from sqlalchemy import text
from .db import engine

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  ts     TEXT    NOT NULL,
  level  TEXT    NOT NULL,
  msg    TEXT    NOT NULL
);
"""

def setup_logging() -> None:
    """Tabel aanmaken en logger koppelen."""
    with engine.begin() as conn:
        conn.exec_driver_sql(TABLE_SQL)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # dubbele handlers voorkomen
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        h = DBHandler()
        fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
        h.setFormatter(fmt)
        root.addHandler(h)

class DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        lvl = record.levelname
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO logs(ts, level, msg) VALUES (:ts, :lvl, :msg)"),
                {"ts": record.asctime if hasattr(record, "asctime") else "", "lvl": lvl, "msg": msg},
            )

def get_events(limit: int = 200, level: str | None = None, q: str | None = None):
    """Lees logs, optioneel gefilterd op level en zoekterm."""
    lvl = level.upper() if level else None
    with engine.begin() as conn:
        if q:
            sql = text("""
                SELECT ts, level, msg
                FROM logs
                WHERE (:lvl IS NULL OR level = :lvl)
                  AND msg LIKE :q
                ORDER BY id DESC
                LIMIT :lim
            """)
            args = {"lvl": lvl, "q": f"%{q}%", "lim": limit}
        else:
            sql = text("""
                SELECT ts, level, msg
                FROM logs
                WHERE (:lvl IS NULL OR level = :lvl)
                ORDER BY id DESC
                LIMIT :lim
            """)
            args = {"lvl": lvl, "lim": limit}
        rows = conn.execute(sql, args).mappings().all()
    return rows
