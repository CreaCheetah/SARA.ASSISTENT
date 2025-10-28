import logging
from sqlalchemy import text
from .db import engine

def conn():
    import sqlite3
    c = sqlite3.connect("/tmp/sara_logs.db", check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

class DBHandler(logging.Handler):
    def emit(self, record):
        try:
            msg  = self.format(record)
            lvl  = record.levelname
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO logs(level, msg) VALUES (:level, :msg)"),
                    {"level": lvl, "msg": msg},
                )
        except Exception:
            # logproblemen mogen je app niet stoppen
            pass

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    dh = DBHandler()
    dh.setFormatter(fmt)
    root.addHandler(dh)

# src/infra/logs.py
def get_events(limit: int = 200, level: str | None = None, q: str | None = None):
    """
    Haal logregels op uit tabel 'events' met optionele filters.
    Verwacht kolommen: ts TIMESTAMPTZ, level TEXT, msg TEXT.
    """
    sql = "SELECT ts, level, msg FROM events"
    conds, params = [], {}

    if level and level.upper() != "ALL":
        conds.append("level = %(level)s")
        params["level"] = level.upper()

    if q:
        conds.append("msg ILIKE %(q)s")
        params["q"] = f"%{q}%"

    if conds:
        sql += " WHERE " + " AND ".join(conds)

    sql += " ORDER BY ts DESC LIMIT %(limit)s"
    params["limit"] = max(1, min(int(limit), 5000))

    with conn() as c:  # gebruikt jouw bestaande conn()
        rows = c.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
