"""Command pattern for console menu actions.

The **Command** design pattern encapsulates each menu action as an object
with a uniform ``execute()`` interface.  The :class:`Menu` class acts as the
*Invoker* – it renders the numbered list and calls ``execute()`` on the
selected command without knowing anything about the action's implementation.

Adding a new feature requires only a new :class:`Command` subclass; the menu
itself and the rest of the application are untouched (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ui import console as con


# ── Command interface ─────────────────────────────────────────────────────────


class Command(ABC):
    """Abstract base for all menu commands (Command pattern – *ConcreteCommand* role)."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Short text shown next to the menu entry number."""
        ...

    @abstractmethod
    def execute(self) -> bool:
        """Perform the action.

        Return ``True`` to stay in the current menu, ``False`` to exit/go back.
        """
        ...


# ── Built-in commands ─────────────────────────────────────────────────────────


class BackCommand(Command):
    """A command that simply signals the menu to exit its loop."""

    def __init__(self, label: str = "Zpět") -> None:
        self._label = label

    @property
    def label(self) -> str:
        return self._label

    def execute(self) -> bool:
        return False


# ── Menu (Invoker) ────────────────────────────────────────────────────────────


class Menu:
    """Renders a numbered list of :class:`Command` objects and dispatches selection.

    This is the *Invoker* in the Command pattern.  It never knows the concrete
    type of the commands it holds – it only calls ``execute()`` and reacts to
    the boolean return value.
    """

    def __init__(self, title: str, subtitle: str = "") -> None:
        self._title = title
        self._subtitle = subtitle
        self._commands: list[Command] = []

    def add(self, command: Command) -> "Menu":
        """Register a command and return *self* for chaining."""
        self._commands.append(command)
        return self

    def run(self) -> None:
        """Display the menu in a loop until a command returns ``False``."""
        while True:
            con.header(self._title, self._subtitle)
            for i, cmd in enumerate(self._commands, 1):
                # Highlight the last entry (usually Back/Logout) in dim
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
