import os
from sqlalchemy import create_engine

url = os.getenv("DATABASE_URL", "")
if not url:
    raise RuntimeError("DATABASE_URL ontbreekt")

if url.startswith("postgres") and "sslmode=" not in url:
    url += ("&" if "?" in url else "?") + "sslmode=require"

engine = create_engine(url, pool_pre_ping=True, future=True)
