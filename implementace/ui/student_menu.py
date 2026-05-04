"""Příkazy studentského menu – UC04 (prohlížení inventáře) a UC06 (rezervace)."""

from __future__ import annotations

from datetime import datetime

from models.entities import Item, User
from services.item_service import (
    AvailableOnlyFilter,
    CategoryFilter,
    FilterStrategy,
    ItemService,
    NoFilter,
)
from services.reservation_service import ReservationService
from ui import console as con
from ui.commands import BackCommand, Command, Menu


# ── UC04 + UC06 ───────────────────────────────────────────────────────────────


class InventoryCommand(Command):
    """UC04 – zobrazí inventář techniky s volitelným filtrováním podle kategorií.

    Příkaz obsahuje vnořené podmenu, ve kterém může student použít
    :class:`FilterStrategy` a případně plynule přejít do UC06.
    """

    def __init__(self, item_svc: ItemService, res_svc: ReservationService, user: User) -> None:
        self._items = item_svc
        self._res   = res_svc
        self._user  = user

    @property
    def label(self) -> str:
        return "Inventář techniky"

    def execute(self) -> bool:
        self._show(NoFilter())
        return True

    # ── Privátní pomocné metody ──────────────────────────────────────────────

    def _show(self, strategy: FilterStrategy) -> None:
        """Vykreslí tabulku exemplářů a zobrazí podmenu dostupných akcí."""
        con.header("Inventář techniky", f"Filtr: {strategy.label}")

        items = self._items.get_items(strategy)
        if not items:
            con.warning("V katalogu aktuálně není žádná technika odpovídající filtru.")
            con.pause()
            return

        self._render_table(items)

        con.section("Akce")
        print(f"  {con.C.CYAN} 1.{con.C.RESET}  Filtrovat podle kategorie")
        print(f"  {con.C.CYAN} 2.{con.C.RESET}  Zobrazit pouze dostupné (Skladem)")
        print(f"  {con.C.CYAN} 3.{con.C.RESET}  Zobrazit vše")
        print(f"  {con.C.CYAN} 4.{con.C.RESET}  {con.C.GREEN}Rezervovat exemplář (UC06){con.C.RESET}")
        print(f"  {con.C.CYAN} 0.{con.C.RESET}  {con.C.DIM}Zpět do hlavního menu{con.C.RESET}")
        con.rule()

        choice = con.prompt_int("Volba", [0, 1, 2, 3, 4], allow_back=True)
        if choice == 1:
            self._apply_category_filter()
        elif choice == 2:
            self._show(AvailableOnlyFilter())
        elif choice == 3:
            self._show(NoFilter())
        elif choice == 4:
            self._reserve_flow(items)
        # 0 / None znamená návrat zpět.

    def _render_table(self, items: list[Item]) -> None:
        rows = [
            [
                str(it.id),
                it.name,
                it.manufacturer,
                it.category_name,
                con.C.status(it.status),
                it.condition,
            ]
            for it in items
        ]
        con.table(
            ["ID", "Název", "Výrobce", "Kategorie", "Stav", "Kondice"],
            rows,
            col_widths=[4, 22, 13, 13, 13, 20],
        )

    def _apply_category_filter(self) -> None:
        categories = self._items.get_categories()
        if not categories:
            con.warning("Žádné kategorie v systému.")
            con.pause()
            return

        con.section("Vyberte kategorii")
        for cat in categories:
            print(f"  {con.C.CYAN}{cat.id:3}.{con.C.RESET}  {cat.name}")
        print(f"  {con.C.CYAN}  0.{con.C.RESET}  {con.C.DIM}Zrušit{con.C.RESET}")
        con.rule()

        cat_ids = [cat.id for cat in categories]
        choice = con.prompt_int("ID kategorie", cat_ids, allow_back=True)
        if choice is None:
            return
        selected = next(c for c in categories if c.id == choice)
        self._show(CategoryFilter(selected))

    def _reserve_flow(self, visible_items: list[Item]) -> None:
        """UC06 – provede studenta vytvořením nové rezervace."""
        available = [it for it in visible_items if it.status == "Skladem"]
        if not available:
            con.warning(
                "Z aktuálně zobrazených exemplářů žádný není ve stavu Skladem.\n"
                "     Zkuste zobrazit vše nebo jiný filtr."
            )
            con.pause()
            return

        con.section("Rezervace – vyberte exemplář (UC06)")
        rows = [
            [str(it.id), it.name, it.manufacturer, it.category_name, it.serial_number]
            for it in available
        ]
        con.table(
            ["ID", "Název", "Výrobce", "Kategorie", "Sériové číslo"],
            rows,
            col_widths=[4, 22, 13, 13, 16],
        )

        item_id = con.prompt_int("ID exempláře k rezervaci", [it.id for it in available])
        if item_id is None:
            return

        date_from = con.prompt_date("Datum vyzvednutí od")
        date_to   = con.prompt_date("Datum vrácení do")

        if date_to <= date_from:
            con.error("Datum 'do' musí být pozdější než datum 'od'.")
            con.pause()
            return

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if date_from < today:
            con.error("Datum 'od' nesmí být v minulosti.")
            con.pause()
            return

        if not self._res.is_available_for_period(item_id, date_from, date_to):
            con.error(
                "Exemplář není v zadaném termínu dostupný – "
                "existuje překrývající se rezervace nebo je exemplář mimo provoz."
            )
            con.pause()
            return

        item = next(it for it in available if it.id == item_id)
        con.blank()
        con.info(f"Exemplář : {item.name}  ({item.serial_number})")
        con.info(f"Termín   : {date_from.strftime('%Y-%m-%d')}  →  {date_to.strftime('%Y-%m-%d')}")
        con.blank()

        if not con.confirm("Potvrdit rezervaci?"):
            con.info("Rezervace zrušena.")
            con.pause()
            return

        res = self._res.create_reservation(self._user, item_id, date_from, date_to)
        con.success(f"Rezervace #{res.id} byla úspěšně vytvořena.")
        con.pause()


# ── Moje rezervace ────────────────────────────────────────────────────────────


class MyReservationsCommand(Command):
    """Zobrazí studentovy aktivní rezervace a případně umožní jejich zrušení."""

    def __init__(self, res_svc: ReservationService, user: User) -> None:
        self._res  = res_svc
        self._user = user

    @property
    def label(self) -> str:
        return "Moje rezervace"

    def execute(self) -> bool:
        con.header("Moje rezervace", f"Student: {self._user.full_name}")
        reservations = self._res.get_user_reservations(self._user.id)

        if not reservations:
            con.warning("Nemáte žádné aktivní rezervace.")
            con.pause()
            return True

        rows = [
            [
                str(r.id),
                r.item_name,
                r.item_serial,
                r.date_from.strftime("%Y-%m-%d"),
                r.date_to.strftime("%Y-%m-%d"),
                con.C.status(r.status),
            ]
            for r in reservations
        ]
        con.table(
            ["ID", "Exemplář", "Sér. číslo", "Od", "Do", "Stav"],
            rows,
            col_widths=[4, 22, 14, 11, 11, 13],
        )

        con.blank()
        if con.confirm("Zrušit některou rezervaci?"):
            res_ids = [r.id for r in reservations]
            res_id  = con.prompt_int("ID rezervace ke zrušení", res_ids)
            if res_id is not None:
                target = next(r for r in reservations if r.id == res_id)
                if con.confirm(f"Opravdu zrušit rezervaci #{res_id} ({target.item_name})?"):
                    self._res.cancel_reservation(res_id, target.item_id)
                    con.success(f"Rezervace #{res_id} byla zrušena.")

        con.pause()
        return True


# ── Tovární funkce ────────────────────────────────────────────────────────────


def build_student_menu(
    user: User,
    item_svc: ItemService,
    res_svc: ReservationService,
) -> Menu:
    """Sestaví a vrátí hlavní menu pro studenta."""
    menu = Menu(
        "Půjčovna školní techniky",
        f"Přihlášen jako: {user.full_name}  ({user.role})",
    )
    menu.add(InventoryCommand(item_svc, res_svc, user))
    menu.add(MyReservationsCommand(res_svc, user))
    menu.add(BackCommand("Odhlásit se"))
    return menu
