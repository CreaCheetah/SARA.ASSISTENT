import os
from sqlalchemy import create_engine

def _url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL ontbreekt")
    # Render geeft soms zonder sslmode; Postgres op Render accepteert ?sslmode=require
    if "sslmode=" not in url and url.startswith("postgres"):
        join = "&" if "?" in url else "?"
        url = f"{url}{join}sslmode=require"
    return url

engine = create_engine(
    _url(),
    pool_pre_ping=True,
    future=True,
)
