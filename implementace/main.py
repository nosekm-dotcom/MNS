"""Půjčovna školní techniky – entry point.

Spuštění::

    python main.py

Přihlašovací údaje pro demo databázi:
    Admin:    admin    / admin123
    Student:  jnovak   / student1
              kprocko  / student2
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure imports work regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from db.database import Database
from db.repositories import (
    CategoryRepository,
    ItemRepository,
    LoanRepository,
    ReservationRepository,
    UserRepository,
)
from services.auth_service import AuthService
from services.item_service import ItemService
from services.loan_service import LoanService
from services.reservation_service import ReservationService
from ui import console as con
from ui.admin_menu import build_admin_menu
from ui.student_menu import build_student_menu


# ── Login screen ──────────────────────────────────────────────────────────────


def _login(auth_svc: AuthService):
    """Render the login form and return an authenticated User (loops on failure)."""
    while True:
        con.header(
            "Půjčovna školní techniky",
            "Systém pro správu výpůjček a rezervací",
        )
        print(f"  {con.C.DIM}Demo přihlašovací údaje:{con.C.RESET}")
        print(f"  {con.C.DIM}  admin   / admin123   (administrátor){con.C.RESET}")
        print(f"  {con.C.DIM}  jnovak  / student1   (student){con.C.RESET}")
        print(f"  {con.C.DIM}  kprocko / student2   (student){con.C.RESET}")
        con.blank()
        con.rule()

        username = con.prompt("Uživatelské jméno")
        password = con.prompt("Heslo")

        user = auth_svc.login(username, password)
        if user is not None:
            return user

        con.error("Neplatné přihlašovací údaje. Zkuste to znovu.")
        con.pause()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    # --- Wiring (Poor-Man's DI) ---
    db = Database()
    db.connect()

    user_repo = UserRepository(db)
    cat_repo  = CategoryRepository(db)
    item_repo = ItemRepository(db)
    res_repo  = ReservationRepository(db)
    loan_repo = LoanRepository(db)

    auth_svc = AuthService(user_repo)
    item_svc = ItemService(item_repo, cat_repo)
    res_svc  = ReservationService(res_repo, item_repo)
    loan_svc = LoanService(loan_repo, item_repo, res_repo)

    # Run expiration check on startup (UC09)
    expired = res_svc.expire_old_reservations()
    if expired:
        print(f"[systém] Automaticky expirováno {expired} rezervaci/í při startu.")

    try:
        while True:
            user = _login(auth_svc)
            if user.role == "admin":
                build_admin_menu(user, item_svc, res_svc, loan_svc, user_repo).run()
            else:
                build_student_menu(user, item_svc, res_svc).run()
    except KeyboardInterrupt:
        con.blank()
        con.info("Aplikace ukončena.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
