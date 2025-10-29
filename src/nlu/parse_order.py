from __future__ import annotations
import re
from typing import List, Tuple
from src.infra import menu as menu_repo
from src.workflows.call_flow import Item

# simpele NL hoeveelheden
QTY_WORDS = {
  "een": 1, "1": 1,
  "twee": 2, "2": 2,
  "drie": 3, "3": 3,
  "vier": 4, "4": 4,
  "vijf": 5, "5": 5
}

# patroon vangt bv. "twee pizza margherita", "1 shoarma schotel", "een pasta bolognese"
PAT = re.compile(
    r"\b(?:(een|twee|drie|vier|vijf|[1-5]))?\s*(pizza|pasta|schotel)?\s*([a-zA-ZÀ-ÿ0-9\- ]+?)\b(?=,| en | plus | met |$)",
    flags=re.IGNORECASE
)

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def parse_items(text: str) -> Tuple[List[Item], List[str]]:
    s = normalize_spaces(text.lower())
    items: List[Item] = []
    misses: List[str] = []
    for m in PAT.finditer(s):
        qty_tok, cat_hint, raw_name = m.groups()
        name_guess = normalize_spaces(raw_name)
        qty = QTY_WORDS.get((qty_tok or "1").lower(), 1)
        hit = menu_repo.lookup(name_guess)
        if not hit:
            # probeer zonder hintwoorden
            for drop in ("pizza", "pasta", "schotel"):
                name_guess = name_guess.replace(drop, "").strip()
            hit = menu_repo.lookup(name_guess)
        if hit:
            cat, canon, price = hit
            # als cat_hint bestaat, overschrijf categorie met hint (bv. "schotel shoarma")
            cat_final = (cat_hint or cat or "").strip().lower() or cat
            if cat_hint and cat_hint.lower() in {"pizza", "pasta", "schotel"}:
                cat_final = cat_hint.lower()
            items.append(Item(name=canon, category=cat_final, qty=qty, unit_price=price))
        else:
            if name_guess:
                misses.append(name_guess)
    # samenvoegen gelijke items
    merged: dict[tuple[str,str,float], Item] = {}
    for it in items:
        key = (it.category, it.name, it.unit_price)
        if key in merged:
            merged[key].qty += it.qty
        else:
            merged[key] = Item(**it.__dict__)
    return list(merged.values()), misses
