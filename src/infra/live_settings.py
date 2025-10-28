from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
import json

from src.infra.db import engine  # bestaand in jouw project

# Enige keys voor Fase 2
DEFAULTS: Dict[str, Any] = {
    "bot_enabled": True,           # kill-switch voor Sara
    "pastas_enabled": True,        # pasta's beschikbaar
    "delay_pizzas_min": 10,        # 10..60 in stappen van 10
    "delay_schotels_min": 10       # 10..60 in stappen van 10
}

_NUM_KEYS = {"delay_pizzas_min", "delay_schotels_min"}
_BOOL_KEYS = {"bot_enabled", "pastas_enabled"}

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

def _validate_payload(updates: Dict[str, Any]) -> Optional[str]:
    for k, v in updates.items():
        if k in _NUM_KEYS:
            if not isinstance(v, int) or v % 10 != 0 or not (10 <= v <= 60):
                return f"{k} must be integer in {{10,20,30,40,50,60}}"
        elif k in _BOOL_KEYS:
            if not isinstance(v, bool):
                return f"{k} must be boolean"
        else:
            return f"unknown key: {k}"
    return None

def _merge_defaults(db_values: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(db_values)
    return merged

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
        row = conn.exec_driver_sql(
            "SELECT value FROM live_settings WHERE key=:k", {"k": key}
        ).first()
    return row[0] if row else DEFAULTS[key]

def set_many(updates: Dict[str, Any]) -> Tuple[bool, str]:
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
                {"k": k, "v": json.dumps(v)},
            )
    return True, "saved"

def set_one(key: str, value: Any) -> Tuple[bool, str]:
    return set_many({key: value})
