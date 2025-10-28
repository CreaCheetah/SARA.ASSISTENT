import logging
from sqlalchemy import text
from .db import engine

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
  id SERIAL PRIMARY KEY,
  ts TIMESTAMPTZ DEFAULT NOW(),
  level TEXT NOT NULL,
  msg   TEXT NOT NULL
);
"""

INSERT_SQL = text("INSERT INTO logs (level, msg) VALUES (:level, :msg)")
SELECT_SQL = text("""
  SELECT ts, level, msg
  FROM logs
  ORDER BY id DESC
  LIMIT :limit
""")

class DBHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            with engine.begin() as c:
                c.execute(INSERT_SQL, {"level": record.levelname, "msg": msg})
        except Exception:
            pass

def setup_logging():
    with engine.begin() as c:
        c.exec_driver_sql(TABLE_SQL)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, DBHandler) for h in root.handlers):
        h = DBHandler()
        h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
        root.addHandler(h)

def get_events(limit: int = 200, level: str | None = None, q: str | None = None):
    sql = "SELECT ts, level, msg FROM logs"
    conds, params = [], {}

    if level and level.upper() != "ALL":
        conds.append("level = :level")
        params["level"] = level.upper()

    if q:
        conds.append("msg ILIKE :q")
        params["q"] = f"%{q}%"

    if conds:
        sql += " WHERE " + " AND ".join(conds)

    sql += " ORDER BY id DESC LIMIT :limit"
    params["limit"] = max(1, min(int(limit), 1000))

    with engine.begin() as conn:
        rows = conn.exec_driver_sql(sql, params).mappings().all()
    return [dict(r) for r in rows]
