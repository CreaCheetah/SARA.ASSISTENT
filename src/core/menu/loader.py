from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from .models import Menu, MenuItem, Variant, Modifier, ModifierOption
from .validator import validate

def _to_item(d: Dict[str, Any]) -> MenuItem:
    variants = [Variant(**v) for v in d.get("variants", [])]
    mods = []
    for m in d.get("modifiers", []):
        opts = [ModifierOption(**o) for o in m.get("options", [])]
        mods.append(Modifier(id=m["id"], type=m["type"], label=m["label"],
                             required=m.get("required", False), options=opts))
    return MenuItem(
        code=d["code"],
        name=d["name"],
        category=d["category"],
        price_eur=d.get("price_eur"),
        available=d.get("available", True),
        variants=variants,
        modifiers=mods,
        aliases=d.get("aliases", []),
        tags=d.get("tags", []),
    )

def load_menu(path: str | Path) -> Menu:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("Menu validation failed:\n" + "\n".join(errors))
    items = [_to_item(x) for x in data.get("items", [])]
    return Menu(meta=data.get("meta", {}),
                categories=data.get("categories", []),
                rules=data.get("rules", []),
                items=items)
