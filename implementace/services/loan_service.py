"""Aplikační logika výpůjček – UC14 (vytvoření) a UC15 (vrácení / UC16)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models.entities import Loan
from db.repositories import ItemRepository, LoanRepository, ReservationRepository


class LoanService:
    """Spravuje celý životní cyklus výpůjček techniky."""

    def __init__(
        self,
        loan_repo: LoanRepository,
        item_repo: ItemRepository,
        res_repo: ReservationRepository,
    ) -> None:
        self._loans = loan_repo
        self._items = item_repo
        self._res = res_repo

    # ── UC14 – Vytvoření výpůjčky ─────────────────────────────────────────────

    def create_loan(
        self,
        user_id: int,
        item_id: int,
        date_due: datetime,
        reservation_id: Optional[int] = None,
    ) -> Loan:
        """Vytvoří novou výpůjčku, označí exemplář jako *Vypůjčeno* a uzavře navázanou rezervaci."""
        loan = self._loans.create(user_id, item_id, date_due, reservation_id)
        self._items.update_status(item_id, "Vypůjčeno")
        if reservation_id is not None:
            self._res.update_status(reservation_id, "Převedena")
        return loan

    # ── UC15 + UC16 – Vrácení výpůjčky ────────────────────────────────────────

    def return_loan(self, loan_id: int, new_status: str, new_condition: str) -> None:
        """Uzavře výpůjčku a aktualizuje stav i kondici exempláře.

        Implementuje **UC15** (evidence vrácení), jehož povinnou součástí je
        také **UC16** (aktualizace stavu a kondice exempláře).
        """
        loan = self._loans.find_by_id(loan_id)
        if loan is None:
            raise ValueError(f"Výpůjčka s ID {loan_id} neexistuje.")
        self._loans.close_loan(loan_id)
        self._items.update_status_and_condition(loan.item_id, new_status, new_condition)

    # ── Dotazy ────────────────────────────────────────────────────────────────

    def get_active_loans(self) -> list[Loan]:
        return self._loans.find_active_loans()

    def get_loan(self, loan_id: int) -> Optional[Loan]:
        return self._loans.find_by_id(loan_id)

    def get_active_loan_for_item(self, item_id: int) -> Optional[Loan]:
        return self._loans.find_active_for_item(item_id)
