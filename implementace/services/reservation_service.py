"""Reservation business logic – UC06 (create) and UC09 (auto-expire)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from models.entities import Reservation, User
from db.repositories import ItemRepository, ReservationRepository

# Students must pick up their reservation within this window after date_from
PICKUP_TOLERANCE = timedelta(hours=24)


class ReservationService:
    """Manages the full lifecycle of reservations."""

    def __init__(self, res_repo: ReservationRepository, item_repo: ItemRepository) -> None:
        self._res = res_repo
        self._items = item_repo

    # ── UC06 – Create reservation ─────────────────────────────────────────────

    def is_available_for_period(
        self, item_id: int, date_from: datetime, date_to: datetime
    ) -> bool:
        """Return ``True`` when no active reservation overlaps the requested window.

        Also returns ``False`` for items that are under repair or retired.
        """
        item = self._items.find_by_id(item_id)
        if item is None or item.status in ("V opravě", "Vyřazeno", "Vypůjčeno"):
            return False
        # Overlap condition: existing.from <= requested.to AND existing.to >= requested.from
        for res in self._res.find_all_active():
            if res.item_id != item_id:
                continue
            if date_from <= res.date_to and date_to >= res.date_from:
                return False
        return True

    def create_reservation(
        self, user: User, item_id: int, date_from: datetime, date_to: datetime
    ) -> Reservation:
        """Persist a new reservation and mark the item as *Rezervováno*."""
        res = self._res.create(user.id, item_id, date_from, date_to)
        self._items.update_status(item_id, "Rezervováno")
        return res

    # ── UC09 – Expiration check ───────────────────────────────────────────────

    def expire_old_reservations(self) -> int:
        """Expire active reservations whose pickup window has closed.

        Marks each qualifying reservation as *Expirovaná* and returns the
        corresponding item to *Skladem*.  Returns the number of expired records.
        This is the implementation of **UC09**.
        """
        cutoff = datetime.now() - PICKUP_TOLERANCE
        expired = self._res.find_expired_candidates(cutoff)
        for res in expired:
            self._res.update_status(res.id, "Expirovaná")
            self._items.update_status(res.item_id, "Skladem")
        return len(expired)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_user_reservations(self, user_id: int) -> list[Reservation]:
        return self._res.find_active_for_user(user_id)

    def get_all_active(self) -> list[Reservation]:
        return self._res.find_all_active()

    def get_reservation(self, res_id: int) -> Optional[Reservation]:
        return self._res.find_by_id(res_id)

    def cancel_reservation(self, res_id: int, item_id: int) -> None:
        """Mark a reservation as *Zrušená* and release the item back to *Skladem*."""
        self._res.update_status(res_id, "Zrušená")
        self._items.update_status(item_id, "Skladem")

    def mark_transferred(self, res_id: int) -> None:
        """Mark a reservation as *Převedena* (converted to a loan)."""
        self._res.update_status(res_id, "Převedena")
