from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Dict, Tuple, Optional
import zoneinfo

AMS = zoneinfo.ZoneInfo("Europe/Amsterdam")

# Tijden
OPEN_FROM = time(16, 0)   # 16:00
DELIVERY_STOP = time(21, 30)  # 21:30
CLOSE_AT = time(22, 0)    # 22:00

@dataclass
class Item:
    name: str
    category: str   # "pizza" | "schotel" | "pasta" | ...
    qty: int
    unit_price: float

def now_ams() -> datetime:
    return datetime.now(tz=AMS)

def greeting(dt: Optional[datetime] = None) -> str:
    dt = dt or now_ams()
    if dt.time() >= time(18,0):
        return ("Goedeavond, u spreekt met Sara, de digitale belassistent van "
                "Ristorante Adam Spanbroek. Waarmee kan ik u helpen?")
    return ("Goedemiddag, u spreekt met Sara, de digitale belassistent van "
            "Ristorante Adam Spanbroek. Waarmee kan ik u helpen?")

def time_status(dt: Optional[datetime] = None) -> str:
    """Geeft '', of een afsluit- of beperkingstekst op basis van tijd."""
    dt = dt or now_ams()
    t = dt.time()
    if t >= CLOSE_AT or t < OPEN_FROM:
        return "Het restaurant is nu gesloten. Morgen vanaf vier uur help ik u graag weer met uw bestelling."
    if t >= DELIVERY_STOP:
        return "Na half tien bezorgen we niet meer, maar afhalen kan nog tot tien uur."
    return ""  # open zonder beperkingen

def category_blocked(categories: List[str], settings: Dict) -> Optional[str]:
    """Retourneert geblokkeerde categorie (bv. 'pasta') of None."""
    blocked = []
    if not settings.get("pastas_enabled", True) and "pasta" in categories:
        blocked.append("pasta")
    return blocked[0] if blocked else None

def combined_order(items: List[Item]) -> bool:
    cats = {i.category for i in items if i.qty > 0}
    total_qty = sum(i.qty for i in items)
    return (len(cats) >= 2) or (total_qty >= 2)

def extra_delay_for(items: List[Item], settings: Dict) -> int:
    cats = {i.category for i in items if i.qty > 0}
    # Neem max vertraging van aanwezige categorieën (voorkomt dubbeltellen)
    candidates = []
    if "pizza" in cats:
        candidates.append(int(settings.get("delay_pizzas_min", 0)))
    if "schotel" in cats:
        candidates.append(int(settings.get("delay_schotels_min", 0)))
    return max(candidates) if candidates else 0

def total_minutes(mode: str, items: List[Item], settings: Dict) -> int:
    mode = (mode or "").lower()
    if mode == "bezorgen":
        base = 60
    else:  # afhalen
        base = 30 if combined_order(items) else 15
    return base + extra_delay_for(items, settings)

def time_phrase(mode: str, minutes: int) -> str:
    mode = (mode or "").lower()
    woord = "bezorgtijd" if mode == "bezorgen" else "afhaaltijd"
    return f"De {woord} is ongeveer {minutes} minuten."

def payment_phrase(mode: str) -> str:
    mode = (mode or "").lower()
    if mode == "bezorgen":
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
