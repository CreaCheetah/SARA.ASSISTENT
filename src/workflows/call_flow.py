from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date, time
from typing import List, Dict, Tuple, Optional
import zoneinfo
import os

AMS = zoneinfo.ZoneInfo("Europe/Amsterdam")

# Openingstijden
OPEN_FROM = time(16, 0)      # 16:00
DELIVERY_STOP = time(21, 30) # 21:30
CLOSE_AT = time(22, 0)       # 22:00


# -------------------------------------------------
#  Tijd & overrides
# -------------------------------------------------
def _env_override_dt() -> Optional[datetime]:
    """Optionele testtijd via env SARA_FORCE_TIME='HH:MM'."""
    s = os.getenv("SARA_FORCE_TIME", "").strip()
    if not s:
        return None
    try:
        hh, mm = s.split(":")
        return datetime.combine(date.today(), time(int(hh), int(mm)), tzinfo=AMS)
    except Exception:
        return None

def now_ams() -> datetime:
    """Gebruik override als aanwezig, anders echte tijd."""
    return _env_override_dt() or datetime.now(tz=AMS)


# -------------------------------------------------
#  Orderstructuur
# -------------------------------------------------
@dataclass
class Item:
    name: str
    category: str
    qty: int
    unit_price: float


# -------------------------------------------------
#  Teksten & logica
# -------------------------------------------------
def greeting(dt: Optional[datetime] = None) -> str:
    dt = dt or now_ams()
    t = dt.time()
    if t < time(12, 0):
        return ("Goedemorgen, u spreekt met Sara, de digitale belassistent van "
                "Ristorante Adam Spanbroek. Waarmee kan ik u helpen?")
    if t < time(18, 0):
        return ("Goedemiddag, u spreekt met Sara, de digitale belassistent van "
                "Ristorante Adam Spanbroek. Waarmee kan ik u helpen?")
    return ("Goedeavond, u spreekt met Sara, de digitale belassistent van "
            "Ristorante Adam Spanbroek. Waarmee kan ik u helpen?")


def time_status(dt: Optional[datetime] = None) -> str:
    """Meld sluiting of bezorgstop."""
    dt = dt or now_ams()
    t = dt.time()
    if t >= CLOSE_AT or t < OPEN_FROM:
        return ("Goeiedag, u spreekt met Sara, de digitale belassistent van "
                "Ristorante Adam Spanbroek. Helaas zijn we op dit moment niet geopend. "
                "Vanaf vier uur kunt u ons weer bereiken.")
    if t >= DELIVERY_STOP:
        return "Na half tien bezorgen we niet meer, maar afhalen kan nog tot tien uur."
    return ""


def category_blocked(categories: List[str], settings: Dict) -> Optional[str]:
    if not settings.get("pastas_enabled", True) and "pasta" in categories:
        return "pasta"
    return None


def combined_order(items: List[Item]) -> bool:
    cats = {i.category for i in items if i.qty > 0}
    total_qty = sum(i.qty for i in items)
    return (len(cats) >= 2) or (total_qty >= 2)


def extra_delay_for(items: List[Item], settings: Dict) -> int:
    """Hoogste categorie-vertraging nemen."""
    cats = {i.category for i in items if i.qty > 0}
    candidates = []
    if "pizza" in cats:
        candidates.append(int(settings.get("delay_pizzas_min", 0)))
    if "schotel" in cats:
        candidates.append(int(settings.get("delay_schotels_min", 0)))
    return max(candidates) if candidates else 0


def total_minutes(mode: str, items: List[Item], settings: Dict) -> int:
    """Basis + stille extra minuten per categorie."""
    mode = (mode or "").lower()
    if mode == "bezorgen":
        base = 60
    else:
        base = 30 if combined_order(items) else 15
    return base + extra_delay_for(items, settings)


def time_phrase(mode: str, minutes: int) -> str:
    woord = "bezorgtijd" if mode.lower() == "bezorgen" else "afhaaltijd"
    return f"De {woord} is ongeveer {minutes} minuten."


def payment_phrase(mode: str) -> str:
    if mode.lower() == "bezorgen":
        return "Betalen kan alleen contant bij de bezorger."
    return "Bij afhalen kunt u contant of met pin betalen."


def summarize(items: List[Item]) -> Tuple[str, float]:
    parts = []
    total = 0.0
    for it in items:
        if it.qty <= 0:
            continue
        parts.append(f"{it.qty}× {it.name}")
        total += it.qty * float(it.unit_price)
    return ("; ".join(parts) if parts else "geen items"), round(total, 2)
