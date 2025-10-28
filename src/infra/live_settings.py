from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
from datetime import datetime
import json
import re

from sqlalchemy import text
from src.infra.db import engine  # jouw bestaande SQLAlchemy engine

# ---- Defaults: één bron van waarheid ----
DEFAULTS: Dict[str, Any] = {
    "bot_hours_daily": {"start": "16:00", "end": "22:00"},
    "delivery_hours": {"start": "17:00", "end": "21:30"},
    "pickup_hours": {"start": "16:00", "end": "21:30"},
    "pickup_flex_enabled": False,  # handmatige verlenging tot 22:00
    "pastas_enabled": True,
    "delay_pizzas_min": 0,        # 0..60
    "delay_schotels_min": 0       # 0..60
}

_NUM_KEYS = {"delay_pizzas_min", "delay_schotels_min"}
_BOOL_KEYS = {"pickup_flex_enabled", "pastas_enabled"}
_TIME_RANGE_KEYS = {"bot_hours_daily", "delivery_hours", "pickup_hours"}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")  # HH:MM

# ---- Tabel aanmaken indien niet aanwezig ----
def ensure_table() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS live_settings (
        key TEXT PRIMARY KEY,
        value JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)

# ---- Validatie ----
def _validate_payload(updates: Dict[str, Any]) -> Optional[str]:
    for k, v in updates.items():
        if k in _NUM_KEYS:
            if not isinstance(v, int) or not (0 <= v <= 60):
                return f"{k} must be integer 0..60"
        elif k in _BOOL_KEYS:
            if not isinstance(v, bool):
                return f"{k} must be boolean"
        elif k in _TIME_RANGE_KEYS:
            if not isinstance(v, dict) or "start" not in v or "end" not in v:
                return f"{k} must be object with start,end"
            if not (_TIME_RE.match(v["start"]) and _TIME_RE.match(v["end"])):
                return f"{k} time format must be HH:MM"
        else:
            return f"unknown key: {k}"
    return None

def _merge_defaults(db_values: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(db_values)
    return merged

# ---- CRUD ----
def get_all() -> Dict[str, Any]:
    ensure_table()
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("SELECT key, value FROM live_settings").all()
    db_vals = {k: v for k, v in rows}
    return _merge_defaults(db_vals)

def get(key: str) -> Any:
    if key not in DEFAULTS:
        raise KeyError(f"unknown key: {key}")
    ensure_table()
    with engine.begin() as conn:
        row = conn.exec_driver_sql("SELECT value FROM live_settings WHERE key=:k", {"k": key}).first()
    if row:
        return row[0]
    return DEFAULTS[key]

def set_many(updates: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Slaat meerdere settings atomair op. Retourneert (ok, message).
    """
    err = _validate_payload(updates)
    if err:
        return False, err

    ensure_table()
    with engine.begin() as conn:
        for k, v in updates.items():
            conn.exec_driver_sql(
                """
                INSERT INTO live_settings(key, value, updated_at)
                VALUES (:k, :v::jsonb, now())
                ON CONFLICT (key) DO UPDATE SET value=:v::jsonb, updated_at=now()
                """,
                {"k": k, "v": json.dumps(v)}
            )
    return True, "saved"

def set_one(key: str, value: Any) -> Tuple[bool, str]:
    return set_many({key: value})

# ---- Runtime helpers ----
def is_within_time_range(key: str, now_hhmm: str) -> bool:
    """
    Controleert of HH:MM binnen het venster van key valt (zelfde dag).
    """
    tr = get(key)  # {"start":"HH:MM","end":"HH:MM"}
    s, e = tr["start"], tr["end"]
    return s <= now_hhmm <= e

def effective_pickup_close(now_hhmm: str) -> str:
    """
    Sluitingstijd afhalen: normaal pickup_hours.end,
    maar als pickup_flex_enabled==True en <= 22:00 dan '22:00'.
    """
    base = get("pickup_hours")["end"]
    flex = get("pickup_flex_enabled")
    return "22:00" if flex and now_hhmm <= "22:00" else base
