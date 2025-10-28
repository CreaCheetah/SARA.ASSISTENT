import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "")
# Render/Neon/PG: SSL vaak verplicht; SQLAlchemy v2 pakt sslmode uit URL
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

def init_db() -> None:
    """Maakt tabellen aan als ze nog niet bestaan."""
    with engine.begin() as conn:
        # Generieke logs
        conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS logs (
          id      BIGSERIAL PRIMARY KEY,
          ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
          level   VARCHAR(10) NOT NULL,
          msg     TEXT NOT NULL
        );
        """)

        # Call-sessies
        conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS call_sessions (
          id           BIGSERIAL PRIMARY KEY,
          call_id      TEXT UNIQUE NOT NULL,
          from_masked  TEXT,
          to_number    TEXT,
          started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
          ended_at     TIMESTAMPTZ,
          duration_sec INTEGER,
          result       TEXT,
          error_code   TEXT,
          error_msg    TEXT
        );
        """)
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_call_sessions_started_at
          ON call_sessions (started_at DESC);
        """)

        # Call-events
        conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS call_events (
          id          BIGSERIAL PRIMARY KEY,
          call_id     TEXT NOT NULL,
          ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
          event       TEXT NOT NULL,
          level       TEXT NOT NULL DEFAULT 'INFO',
          data_json   JSONB,
          latency_ms  INTEGER,
          status_code INTEGER
        );
        """)
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_call_events_call_ts
          ON call_events (call_id, ts);
        """)
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_call_events_event
          ON call_events (event);
        """)
        conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_call_events_level
          ON call_events (level);
        """)
