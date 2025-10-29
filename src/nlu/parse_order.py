from __future__ import annotations
import re
from typing import List, Tuple
from src.infra import menu as menu_repo
from src.workflows.call_flow import Item

# NL hoeveelheden (1–10)
QTY_WORDS = {
    "een": 1, "één": 1, "1": 1,
    "twee": 2, "2": 2,
    "drie": 3, "3": 3,
    "vier": 4, "4": 4,
    "vijf": 5, "5": 5,
    "zes": 6, "6": 6,
    "zeven": 7, "7": 7,
    "acht": 8, "8": 8,
    "negen": 9, "9": 9,
    "tien": 10, "10": 10,
}

# categorie in enkel- of meervoud + bezit-s
CAT_RE = r"(pizza(?:'s|’s|s)?|pizzas?|pasta(?:'s|’s|s)?|schotel(?:'s|’s|s)?|schotels?)"

# vang segmenten gescheiden door komma's of 'en'
PAT = re.compile(
    rf"\b(?:(een|één|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|[1-9]|10))?\s*{CAT_RE}?\s*([a-zA-ZÀ-ÿ0-9\- ]+?)\b(?=,| en | plus | met | en een |$)",
    flags=re.IGNORECASE,
)

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def _singular_cat(cat_hint: str | None) -> str | None:
    if not cat_hint:
        return None
    c = cat_hint.lower().strip()
    c = c.replace("’s", "").replace("'s", "")
    if c.endswith("s") and c not in {"pasta"}:
        c = c[:-1]
    if c == "pizzas":
        c = "pizza"
    return c if c in {"pizza", "pasta", "schotel"} else None

def _normalize_name(n: str) -> str:
    n = normalize_spaces(n.lower())
    n = n.replace("’s", "").replace("'s", "")  # b.v. margherita's
    # verwijder losse categorie-woorden in naam
    for drop in ("pizza", "pasta", "schotel", "pizzas", "schotels"):
        n = re.sub(rf"\b{drop}\b", "", n).strip()
    return normalize_spaces(n)

def parse_items(text: str) -> Tuple[List[Item], List[str]]:
    s = normalize_spaces(text.lower())
    items: List[Item] = []
    misses: List[str] = []

    for m in PAT.finditer(s):
        qty_tok, cat_hint, raw_name = m.groups()
        qty = QTY_WORDS.get((qty_tok or "1").lower(), 1)
        cat = _singular_cat(cat_hint)
        name_guess = _normalize_name(raw_name)

        hit = menu_repo.lookup(name_guess)
        if not hit and name_guess:
            # nogmaals proberen zonder laatste s
            if name_guess.endswith("s"):
                hit = menu_repo.lookup(name_guess[:-1])

        if hit:
            menu_cat, canon, price = hit
            cat_final = cat or menu_cat
            items.append(Item(name=canon, category=cat_final, qty=qty, unit_price=price))
        else:
            if name_guess:
                misses.append(name_guess)

    # samenvoegen gelijke items
    merged: dict[tuple[str, str, float], Item] = {}
    for it in items:
        key = (it.category, it.name, it.unit_price)
        if key in merged:
            merged[key].qty += it.qty
        else:
            merged[key] = Item(**it.__dict__)
    return list(merged.values()), misses
