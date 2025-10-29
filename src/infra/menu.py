from __future__ import annotations
import json, os
from typing import Dict, Any

MENU_PATH = os.getenv("SARA_MENU_JSON", "data/menu.json")

_DEFAULT_MENU = {
  "pizza": {
    "margherita": 12.0,
    "salami": 13.5,
    "funghi": 13.0
  },
  "schotel": {
    "shoarma": 15.0,
    "kebab": 15.0
  },
  "pasta": {
    "bolognese": 14.0,
    "carbonara": 14.5
  }
}

_SYNONYMS = {
  "margarita": "margherita",
  "fungi": "funghi",
  "shoarma schotel": "shoarma",
  "kebap": "kebab",
  "pasta bolognaise": "bolognese",
}

def _ensure_file():
    os.makedirs(os.path.dirname(MENU_PATH), exist_ok=True)
    if not os.path.exists(MENU_PATH):
        with open(MENU_PATH, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_MENU, f, ensure_ascii=False, indent=2)

def load_menu() -> Dict[str, Dict[str, float]]:
    _ensure_file()
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    # normaliseer keys
    norm = {}
    for cat, items in (data or {}).items():
        catn = cat.strip().lower()
        norm[catn] = {}
        for name, price in (items or {}).items():
            norm[catn][name.strip().lower()] = float(price)
    return norm

def canonical_name(name: str) -> str:
    n = name.strip().lower()
    return _SYNONYMS.get(n, n)

def lookup(name: str) -> tuple[str, str, float] | None:
    """Zoek (category, canonical_item, price) op basis van itemnaam."""
    n = canonical_name(name)
    menu = load_menu()
    for cat, items in menu.items():
        if n in items:
            return cat, n, float(items[n])
    # heuristiek: afkappen van woorden ("pizza margherita" -> "margherita")
    parts = [p for p in n.split() if p not in {"pizza", "pasta", "schotel"}]
    if parts:
        nn = " ".join(parts)
        for cat, items in menu.items():
            if nn in items:
                return cat, nn, float(items[nn])
    return None
