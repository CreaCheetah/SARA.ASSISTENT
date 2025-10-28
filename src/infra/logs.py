import logging
from sqlalchemy import text
from .db import engine

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

def get_events(limit: int = 200):
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT ts, level, msg FROM logs ORDER BY id DESC LIMIT :lim"),
            {"lim": limit},
        ).fetchall()
    return [{"ts": r.ts, "level": r.level, "msg": r.msg} for r in rows]
