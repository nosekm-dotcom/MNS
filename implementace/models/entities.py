"""Datové třídy doménových entit systému Půjčovna školní techniky."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Uživatel systému, tedy student nebo administrátor."""

    id: int
    username: str
    full_name: str
    email: str
    role: str  # 'student' | 'admin'
    password_hash: str = field(repr=False)


@dataclass
class Category:
    """Kategorie techniky, například fotoaparát, objektiv nebo stativ."""

    id: int
    name: str
    description: str


@dataclass
class Item:
    """Konkrétní fyzický kus techniky, tedy evidovaný exemplář.

    Životní cyklus stavu:
        Skladem → Rezervováno → Vypůjčeno → Skladem (po vrácení)
        Skladem → V opravě → Skladem
        * → Vyřazeno (koncový stav)
    """

    id: int
    category_id: int
    name: str
    manufacturer: str
    serial_number: str
    status: str       # 'Skladem' | 'Rezervováno' | 'Vypůjčeno' | 'V opravě' | 'Vyřazeno'
    condition: str    # Slovní popis kondice exempláře
    notes: str
    category_name: str = ""   # Denormalizováno pro zobrazení; doplní repository přes JOIN


@dataclass
class Reservation:
    """Rezervace exempláře studentem pro budoucí časové období (UC06)."""

    id: int
    user_id: int
    item_id: int
    date_from: datetime
    date_to: datetime
    status: str        # 'Aktivní' | 'Expirovaná' | 'Zrušená' | 'Převedena'
    created_at: datetime
    # Denormalizovaná pole pro zobrazení
    user_name: str = ""
    item_name: str = ""
    item_serial: str = ""


@dataclass
class Loan:
    """Aktivní nebo již ukončená výpůjčka exempláře techniky (UC14, UC15)."""

    id: int
    reservation_id: Optional[int]   # None při přímém vytvoření administrátorem
    user_id: int
    item_id: int
    date_loaned: datetime
    date_due: datetime
    date_returned: Optional[datetime]
    status: str   # 'Aktivní' | 'Ukončená'
    notes: str
    # Denormalizovaná pole pro zobrazení
    user_name: str = ""
    item_name: str = ""
    item_serial: str = ""
