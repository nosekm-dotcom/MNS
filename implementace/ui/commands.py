"""Implementace návrhového vzoru Command pro akce konzolového menu.

Návrhový vzor **Command** zapouzdřuje každou akci menu jako objekt se
sjednoceným rozhraním ``execute()``. Třída :class:`Menu` zde vystupuje jako
*Invoker* – vykreslí očíslovaný seznam a zavolá ``execute()`` na vybraném
příkazu, aniž by znala detaily jeho implementace.

Přidání nové funkce tak vyžaduje pouze novou podtřídu :class:`Command`;
samotné menu ani zbytek aplikace není nutné měnit (princip Open/Closed).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ui import console as con


# ── Rozhraní Command ──────────────────────────────────────────────────────────


class Command(ABC):
    """Abstraktní základ pro všechny příkazy menu."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Krátký text zobrazený vedle čísla položky menu."""
        ...

    @abstractmethod
    def execute(self) -> bool:
        """Provede akci.

        Vrátí ``True`` pro setrvání v aktuálním menu, ``False`` pro návrat zpět.
        """
        ...


# ── Vestavěné příkazy ─────────────────────────────────────────────────────────


class BackCommand(Command):
    """Příkaz, který pouze signalizuje ukončení aktuální smyčky menu."""

    def __init__(self, label: str = "Zpět") -> None:
        self._label = label

    @property
    def label(self) -> str:
        return self._label

    def execute(self) -> bool:
        return False


# ── Menu (Invoker) ────────────────────────────────────────────────────────────


class Menu:
    """Vykreslí číslovaný seznam objektů :class:`Command` a odbaví volbu uživatele.

    V rámci vzoru Command jde o roli *Invoker*. Nikdy nepotřebuje znát
    konkrétní typ uložených příkazů; pouze volá ``execute()`` a reaguje na
    vrácenou booleovskou hodnotu.
    """

    def __init__(self, title: str, subtitle: str = "") -> None:
        self._title = title
        self._subtitle = subtitle
        self._commands: list[Command] = []

    def add(self, command: Command) -> "Menu":
        """Zaregistruje příkaz a vrátí *self* pro řetězení volání."""
        self._commands.append(command)
        return self

    def run(self) -> None:
        """Zobrazuje menu ve smyčce, dokud některý příkaz nevrátí ``False``."""
        while True:
            con.header(self._title, self._subtitle)
            for i, cmd in enumerate(self._commands, 1):
                # Poslední položku, typicky Zpět nebo Odhlásit, zvýrazní méně nápadně.
                colour = con.C.DIM if i == len(self._commands) else ""
                print(f"  {con.C.CYAN}{i:2}.{con.C.RESET}  {colour}{cmd.label}{con.C.RESET}")
            con.blank()
            con.rule()
            valid = list(range(1, len(self._commands) + 1))
            choice = con.prompt_int("Volba", valid, allow_back=False)
            if choice is None:
                continue
            result = self._commands[choice - 1].execute()
            if result is False:
                break
