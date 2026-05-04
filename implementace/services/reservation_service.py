"""Aplikační logika rezervací – UC06 (vytvoření) a UC09 (automatická expirace)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from models.entities import Reservation, User
from db.repositories import ItemRepository, ReservationRepository

# Student si musí rezervaci vyzvednout nejpozději v tomto okně po `date_from`.
PICKUP_TOLERANCE = timedelta(hours=24)


class ReservationService:
    """Spravuje celý životní cyklus rezervací."""

    def __init__(self, res_repo: ReservationRepository, item_repo: ItemRepository) -> None:
        self._res = res_repo
        self._items = item_repo

    # ── UC06 – Vytvoření rezervace ────────────────────────────────────────────

    def is_available_for_period(
        self, item_id: int, date_from: datetime, date_to: datetime
    ) -> bool:
        """Vrátí ``True``, pokud se požadovaný interval nepřekrývá s aktivní rezervací.

        Zároveň vrací ``False`` pro exempláře v opravě, vyřazené nebo vypůjčené.
        """
        item = self._items.find_by_id(item_id)
        if item is None or item.status in ("V opravě", "Vyřazeno", "Vypůjčeno"):
            return False
        # Podmínka překryvu: existující.od <= požadované.do A existující.do >= požadované.od.
        for res in self._res.find_all_active():
            if res.item_id != item_id:
                continue
            if date_from <= res.date_to and date_to >= res.date_from:
                return False
        return True

    def create_reservation(
        self, user: User, item_id: int, date_from: datetime, date_to: datetime
    ) -> Reservation:
        """Uloží novou rezervaci a nastaví exemplář do stavu *Rezervováno*."""
        res = self._res.create(user.id, item_id, date_from, date_to)
        self._items.update_status(item_id, "Rezervováno")
        return res

    # ── UC09 – Kontrola expirace ──────────────────────────────────────────────

    def expire_old_reservations(self) -> int:
        """Exspiruje aktivní rezervace, kterým už vypršelo okno pro vyzvednutí.

        Každou odpovídající rezervaci označí jako *Expirovaná* a příslušný
        exemplář vrátí do stavu *Skladem*. Vrací počet takto expirovaných
        záznamů. Jde o implementaci případu užití **UC09**.
        """
        cutoff = datetime.now() - PICKUP_TOLERANCE
        expired = self._res.find_expired_candidates(cutoff)
        for res in expired:
            self._res.update_status(res.id, "Expirovaná")
            self._items.update_status(res.item_id, "Skladem")
        return len(expired)

    # ── Dotazy ────────────────────────────────────────────────────────────────

    def get_user_reservations(self, user_id: int) -> list[Reservation]:
        return self._res.find_active_for_user(user_id)

    def get_all_active(self) -> list[Reservation]:
        return self._res.find_all_active()

    def get_reservation(self, res_id: int) -> Optional[Reservation]:
        return self._res.find_by_id(res_id)

    def cancel_reservation(self, res_id: int, item_id: int) -> None:
        """Označí rezervaci jako *Zrušená* a uvolní exemplář zpět do *Skladem*."""
        self._res.update_status(res_id, "Zrušená")
        self._items.update_status(item_id, "Skladem")

    def mark_transferred(self, res_id: int) -> None:
        """Označí rezervaci jako *Převedena*, tedy převedenou na výpůjčku."""
        self._res.update_status(res_id, "Převedena")
