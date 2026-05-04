"""Domain entity dataclasses for the Půjčovna školní techniky system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """System user – either a student or an administrator."""

    id: int
    username: str
    full_name: str
    email: str
    role: str  # 'student' | 'admin'
    password_hash: str = field(repr=False)


@dataclass
class Category:
    """Equipment category (e.g. Fotoaparát, Objektiv, Stativ)."""

    id: int
    name: str
    description: str


@dataclass
class Item:
    """A specific physical piece of equipment – an exemplář (inventory unit).

    Status lifecycle:
        Skladem → Rezervováno → Vypůjčeno → Skladem (after return)
        Skladem → V opravě → Skladem
        * → Vyřazeno (terminal)
    """

    id: int
    category_id: int
    name: str
    manufacturer: str
    serial_number: str
    status: str       # 'Skladem' | 'Rezervováno' | 'Vypůjčeno' | 'V opravě' | 'Vyřazeno'
    condition: str    # Free-text condition description
    notes: str
    category_name: str = ""   # Denormalised for display; populated by repository JOIN


@dataclass
class Reservation:
    """A student's booking of an item for a future time window (UC06)."""

    id: int
    user_id: int
    item_id: int
    date_from: datetime
    date_to: datetime
    status: str        # 'Aktivní' | 'Expirovaná' | 'Zrušená' | 'Převedena'
    created_at: datetime
    # Denormalised display fields
    user_name: str = ""
    item_name: str = ""
    item_serial: str = ""


@dataclass
class Loan:
    """An active or completed loan of a piece of equipment (UC14, UC15)."""

    id: int
    reservation_id: Optional[int]   # None when created directly by admin
    user_id: int
    item_id: int
    date_loaned: datetime
    date_due: datetime
    date_returned: Optional[datetime]
    status: str   # 'Aktivní' | 'Ukončená'
    notes: str
    # Denormalised display fields
    user_name: str = ""
    item_name: str = ""
    item_serial: str = ""
