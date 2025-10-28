from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ModifierOption:
    key: str
    label: str
    price_delta_eur: float = 0.0

@dataclass
class Modifier:
    id: str
    type: str  # "choice" | "toggle" | "qty"
    label: str
    required: bool = False
    options: List[ModifierOption] = field(default_factory=list)

@dataclass
class Variant:
    key: str
    label: str
    price_eur: Optional[float] = None

@dataclass
class MenuItem:
    code: str
    name: str
    category: str
    price_eur: Optional[float] = None
    available: bool = True
    variants: List[Variant] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class Menu:
    meta: Dict[str, Any]
    categories: List[str]
    rules: List[Dict[str, Any]]
    items: List[MenuItem]
