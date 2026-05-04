"""Administrator menu commands – UC09, UC14, UC15, UC16."""

from __future__ import annotations

from datetime import datetime

from models.entities import User
from services.item_service import ItemService
from services.loan_service import LoanService
from services.reservation_service import ReservationService
from db.repositories import UserRepository
from ui import console as con
from ui.commands import BackCommand, Command, Menu

# Allowed item statuses for admin selection
_STATUSES = ["Skladem", "Rezervováno", "Vypůjčeno", "V opravě", "Vyřazeno"]


# ── Active reservations ───────────────────────────────────────────────────────


class ListReservationsCommand(Command):
    """Display all currently active reservations."""

    def __init__(self, res_svc: ReservationService) -> None:
        self._res = res_svc

    @property
    def label(self) -> str:
        return "Přehled aktivních rezervací"

    def execute(self) -> bool:
        con.header("Aktivní rezervace")
        reservations = self._res.get_all_active()

        if not reservations:
            con.warning("Žádné aktivní rezervace.")
        else:
            rows = [
                [
                    str(r.id),
                    r.user_name,
                    r.item_name,
                    r.item_serial,
                    r.date_from.strftime("%Y-%m-%d"),
                    r.date_to.strftime("%Y-%m-%d"),
                    con.C.status(r.status),
                ]
                for r in reservations
            ]
            con.table(
                ["ID", "Student", "Exemplář", "Sér. číslo", "Od", "Do", "Stav"],
                rows,
                col_widths=[4, 20, 20, 14, 11, 11, 13],
            )

        con.pause()
        return True


# ── UC14 – Create loan ────────────────────────────────────────────────────────


class CreateLoanCommand(Command):
    """UC14 – Create a new loan, either from an existing reservation or directly."""

    def __init__(
        self,
        loan_svc: LoanService,
        res_svc: ReservationService,
        item_svc: ItemService,
        user_repo: UserRepository,
    ) -> None:
        self._loans     = loan_svc
        self._res       = res_svc
        self._items     = item_svc
        self._user_repo = user_repo

    @property
    def label(self) -> str:
        return "Vytvořit výpůjčku  (UC14)"

    def execute(self) -> bool:
        con.header("Vytvořit výpůjčku  –  UC14")
        print(f"  {con.C.CYAN} 1.{con.C.RESET}  Z existující rezervace")
        print(f"  {con.C.CYAN} 2.{con.C.RESET}  Přímo (bez rezervace)")
        print(f"  {con.C.CYAN} 0.{con.C.RESET}  {con.C.DIM}Zpět{con.C.RESET}")
        con.rule()

        choice = con.prompt_int("Volba", [0, 1, 2], allow_back=True)
        if choice == 1:
            self._from_reservation()
        elif choice == 2:
            self._direct()
        return True

    # ── private helpers ───────────────────────────────────────────────────────

    def _from_reservation(self) -> None:
        """Convert an active reservation into a loan."""
        reservations = self._res.get_all_active()
        if not reservations:
            con.warning("Žádné aktivní rezervace k převodu na výpůjčku.")
            con.pause()
            return

        con.section("Aktivní rezervace")
        rows = [
            [str(r.id), r.user_name, r.item_name, r.item_serial,
             r.date_from.strftime("%Y-%m-%d"), r.date_to.strftime("%Y-%m-%d")]
            for r in reservations
        ]
        con.table(
            ["ID", "Student", "Exemplář", "Sér. číslo", "Od", "Do"],
            rows,
            col_widths=[4, 20, 20, 14, 11, 11],
        )

        res_ids = [r.id for r in reservations]
        res_id  = con.prompt_int("ID rezervace pro převod", res_ids)
        if res_id is None:
            return

        res      = self._res.get_reservation(res_id)
        date_due = con.prompt_date("Datum splatnosti výpůjčky")

        if not con.confirm(
            f"Vytvořit výpůjčku pro {res.user_name} "  # type: ignore[union-attr]
            f"({res.item_name}) do {date_due.strftime('%Y-%m-%d')}?"
        ):
            return

        loan = self._loans.create_loan(res.user_id, res.item_id, date_due, res_id)  # type: ignore[union-attr]
        con.success(
            f"Výpůjčka #{loan.id} vytvořena pro {res.user_name}. "  # type: ignore[union-attr]
            f"Splatnost: {date_due.strftime('%Y-%m-%d')}."
        )
        con.pause()

    def _direct(self) -> None:
        """Create a loan without a prior reservation."""
        available = [it for it in self._items.get_items() if it.status == "Skladem"]
        if not available:
            con.warning("Žádný exemplář momentálně ve stavu Skladem.")
            con.pause()
            return

        con.section("Dostupné exempláře")
        rows = [[str(it.id), it.name, it.manufacturer, it.serial_number] for it in available]
        con.table(
            ["ID", "Název", "Výrobce", "Sér. číslo"],
            rows,
            col_widths=[4, 24, 14, 16],
        )
        item_id = con.prompt_int("ID exempláře", [it.id for it in available])
        if item_id is None:
            return

        students = self._user_repo.find_students()
        con.section("Studenti")
        rows2 = [[str(u.id), u.full_name, u.username, u.email] for u in students]
        con.table(["ID", "Jméno", "Login", "E-mail"], rows2, col_widths=[4, 24, 12, 28])

        student_ids = [u.id for u in students]
        user_id = con.prompt_int("ID studenta", student_ids)
        if user_id is None:
            return

        date_due = con.prompt_date("Datum splatnosti výpůjčky")

        student = next(u for u in students if u.id == user_id)
        item    = next(it for it in available if it.id == item_id)

        if not con.confirm(
            f"Vytvořit výpůjčku: {item.name} → {student.full_name} "
            f"do {date_due.strftime('%Y-%m-%d')}?"
        ):
            return

        loan = self._loans.create_loan(user_id, item_id, date_due)
        con.success(f"Výpůjčka #{loan.id} vytvořena. Splatnost: {date_due.strftime('%Y-%m-%d')}.")
        con.pause()


# ── UC15 + UC16 – Return loan ─────────────────────────────────────────────────


class ReturnLoanCommand(Command):
    """UC15 – Record the return of a loan; includes UC16 (update item condition)."""

    def __init__(self, loan_svc: LoanService) -> None:
        self._loans = loan_svc

    @property
    def label(self) -> str:
        return "Evidovat vrácení výpůjčky  (UC15)"

    def execute(self) -> bool:
        con.header("Vrácení výpůjčky  –  UC15")
        active = self._loans.get_active_loans()

        if not active:
            con.warning("Žádné aktivní výpůjčky.")
            con.pause()
            return True

        rows = [
            [
                str(l.id),
                l.user_name,
                l.item_name,
                l.item_serial,
                l.date_loaned.strftime("%Y-%m-%d"),
                l.date_due.strftime("%Y-%m-%d"),
            ]
            for l in active
        ]
        con.table(
            ["ID", "Student", "Exemplář", "Sér. číslo", "Vypůjčeno", "Splatnost"],
            rows,
            col_widths=[4, 20, 20, 14, 11, 11],
        )

        loan_id = con.prompt_int("ID výpůjčky k uzavření", [l.id for l in active])
        if loan_id is None:
            return True

        loan = next(l for l in active if l.id == loan_id)
        con.blank()
        con.info(f"Vracíte: {con.C.b(loan.item_name)}  ({loan.item_serial})")
        con.info(f"Student: {loan.user_name}")
        con.blank()

        # UC16 – inline: update status and condition
        con.section("Aktualizace stavu exempláře  –  UC16")
        for i, s in enumerate(_STATUSES, 1):
            print(f"  {con.C.CYAN}{i}.{con.C.RESET}  {con.C.status(s)}")
        con.rule()

        status_idx = con.prompt_int("Nový stav exempláře", list(range(1, len(_STATUSES) + 1)), allow_back=False)
        if status_idx is None:
            return True
        new_status = _STATUSES[status_idx - 1]
        new_condition = con.prompt("Kondice exempláře", "V pořádku")

        if not con.confirm(f"Potvrdit vrácení výpůjčky #{loan_id}?"):
            return True

        try:
            self._loans.return_loan(loan_id, new_status, new_condition)
        except ValueError as exc:
            con.error(str(exc))
            con.pause()
            return True

        con.success(f"Výpůjčka #{loan_id} uzavřena. Exemplář je nyní: {con.C.status(new_status)}.")
        con.pause()
        return True


# ── UC16 – standalone item update ─────────────────────────────────────────────


class UpdateItemCommand(Command):
    """UC16 – Update the status and condition of any item (admin standalone action)."""

    def __init__(self, item_svc: ItemService) -> None:
        self._items = item_svc

    @property
    def label(self) -> str:
        return "Aktualizovat stav / kondici exempláře  (UC16)"

    def execute(self) -> bool:
        con.header("Aktualizovat exemplář  –  UC16")
        items = self._items.get_items(include_retired=True)

        rows = [
            [str(it.id), it.name, it.manufacturer, it.serial_number,
             con.C.status(it.status), it.condition]
            for it in items
        ]
        con.table(
            ["ID", "Název", "Výrobce", "Sér. číslo", "Stav", "Kondice"],
            rows,
            col_widths=[4, 22, 13, 16, 13, 22],
        )

        item_id = con.prompt_int("ID exempláře", [it.id for it in items])
        if item_id is None:
            return True

        item = next(it for it in items if it.id == item_id)
        con.blank()
        con.info(f"Exemplář: {item.name}  ({item.serial_number})")
        con.info(f"Aktuální stav: {con.C.status(item.status)}  |  Kondice: {item.condition}")
        con.blank()

        con.section("Nový stav")
        for i, s in enumerate(_STATUSES, 1):
            print(f"  {con.C.CYAN}{i}.{con.C.RESET}  {con.C.status(s)}")
        con.rule()

        status_idx = con.prompt_int("Volba", list(range(1, len(_STATUSES) + 1)), allow_back=False)
        if status_idx is None:
            return True
        new_status    = _STATUSES[status_idx - 1]
        new_condition = con.prompt("Nová kondice", item.condition)

        if not con.confirm(f"Uložit změny pro exemplář #{item_id}?"):
            return True

        self._items.update_status_and_condition(item_id, new_status, new_condition)
        con.success(f"Exemplář #{item_id} aktualizován → {con.C.status(new_status)}.")
        con.pause()
        return True


# ── UC09 – Manual expiration trigger ─────────────────────────────────────────


class ExpireReservationsCommand(Command):
    """UC09 – Run the reservation-expiration check on demand.

    In production this would be triggered automatically by a scheduler.
    The admin can also run it manually from this menu.
    """

    def __init__(self, res_svc: ReservationService) -> None:
        self._res = res_svc

    @property
    def label(self) -> str:
        return "Zkontrolovat expirované rezervace  (UC09)"

    def execute(self) -> bool:
        con.header("Kontrola expirací  –  UC09")
        con.info("Hledám rezervace, jejichž lhůta pro vyzvednutí vypršela …")
        con.blank()

        count = self._res.expire_old_reservations()
        if count:
            con.success(
                f"Expirováno {count} rezervace/í. "
                "Příslušná technika byla vrácena do stavu Skladem."
            )
        else:
            con.info("Žádné rezervace k expiraci – vše je v pořádku.")

        con.pause()
        return True


# ── Active loans overview ─────────────────────────────────────────────────────


class ListLoansCommand(Command):
    """Display all currently active loans."""

    def __init__(self, loan_svc: LoanService) -> None:
        self._loans = loan_svc

    @property
    def label(self) -> str:
        return "Přehled aktivních výpůjček"

    def execute(self) -> bool:
        con.header("Aktivní výpůjčky")
        loans = self._loans.get_active_loans()

        if not loans:
            con.warning("Žádné aktivní výpůjčky.")
        else:
            today = datetime.now().date()
            rows = []
            for l in loans:
                due = l.date_due.date()
                due_str = l.date_due.strftime("%Y-%m-%d")
                if due < today:
                    due_str = con.C.err(due_str + " !")   # overdue highlight
                rows.append([
                    str(l.id), l.user_name, l.item_name, l.item_serial,
                    l.date_loaned.strftime("%Y-%m-%d"), due_str,
                ])
            con.table(
                ["ID", "Student", "Exemplář", "Sér. číslo", "Vypůjčeno", "Splatnost"],
                rows,
                col_widths=[4, 20, 20, 14, 11, 14],
            )

        con.pause()
        return True


# ── Factory function ──────────────────────────────────────────────────────────


def build_admin_menu(
    user: User,
    item_svc: ItemService,
    res_svc: ReservationService,
    loan_svc: LoanService,
    user_repo: UserRepository,
) -> Menu:
    """Assemble and return the administrator main menu."""
    menu = Menu(
        "Půjčovna školní techniky  –  Administrace",
        f"Přihlášen jako: {user.full_name}  ({user.role})",
    )
    menu.add(ListReservationsCommand(res_svc))
    menu.add(ListLoansCommand(loan_svc))
    menu.add(CreateLoanCommand(loan_svc, res_svc, item_svc, user_repo))
    menu.add(ReturnLoanCommand(loan_svc))
    menu.add(UpdateItemCommand(item_svc))
    menu.add(ExpireReservationsCommand(res_svc))
    menu.add(BackCommand("Odhlásit se"))
    return menu
