from __future__ import annotations
from typing import Dict, Optional
import unicodedata
import re
from .models import Menu, MenuItem

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s

class MenuCatalog:
    def __init__(self, menu: Menu):
        self.menu = menu
        self.by_code: Dict[str, MenuItem] = {it.code: it for it in menu.items}
        self.name_map: Dict[str, str] = {}
        for it in menu.items:
            self.name_map[_norm(it.name)] = it.code
            for a in it.aliases:
                self.name_map[_norm(a)] = it.code

    def get(self, code: str) -> Optional[MenuItem]:
        return self.by_code.get(code)

    def find_by_text(self, text: str) -> Optional[MenuItem]:
        key = _norm(text)
        code = self.name_map.get(key)
        return self.by_code.get(code) if code else None
