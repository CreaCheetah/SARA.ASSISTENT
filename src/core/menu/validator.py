from __future__ import annotations
from typing import Dict, Any, List, Set

def validate(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    cats: Set[str] = set(data.get("categories", []))
    seen_codes: Set[str] = set()

    if not cats:
        errors.append("categories list is empty")

    for idx, it in enumerate(data.get("items", []), start=1):
        code = it.get("code")
        name = it.get("name")
        cat  = it.get("category")
        if not code or not isinstance(code, str):
            errors.append(f"item[{idx}] missing code")
        elif code in seen_codes:
            errors.append(f"duplicate code: {code}")
        else:
            seen_codes.add(code)

        if not name:
            errors.append(f"{code}: missing name")
        if cat not in cats:
            errors.append(f"{code}: unknown category '{cat}'")

        price = it.get("price_eur")
        if price is not None and not isinstance(price, (int, float)):
            errors.append(f"{code}: price_eur must be number or null")

        for v in it.get("variants", []):
            vp = v.get("price_eur")
            if vp is not None and not isinstance(vp, (int, float)):
                errors.append(f"{code}: variant {v.get('key')} price_eur must be number or null")

    return errors
