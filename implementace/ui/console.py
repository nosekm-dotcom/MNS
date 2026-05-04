"""Console UI helpers – colours, tables, prompts and layout primitives."""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from typing import Any


# ── ANSI colours ──────────────────────────────────────────────────────────────


class C:
    """ANSI escape-code constants."""

    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    _STATUS: dict[str, str] = {
        "Skladem":     "\033[92m",   # green
        "Rezervováno": "\033[93m",   # yellow
        "Vypůjčeno":   "\033[91m",   # red
        "V opravě":    "\033[95m",   # magenta
        "Vyřazeno":    "\033[2m",    # dim
    }

    @classmethod
    def status(cls, text: str) -> str:
        """Wrap *text* in the colour associated with that item status."""
        colour = cls._STATUS.get(text, cls.RESET)
        return f"{colour}{text}{cls.RESET}"

    @classmethod
    def b(cls, text: str) -> str:
        return f"{cls.BOLD}{text}{cls.RESET}"

    @classmethod
    def dim(cls, text: str) -> str:
        return f"{cls.DIM}{text}{cls.RESET}"

    @classmethod
    def ok(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def warn(cls, text: str) -> str:
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def err(cls, text: str) -> str:
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def hi(cls, text: str) -> str:
        return f"{cls.CYAN}{text}{cls.RESET}"


# ── Terminal geometry ─────────────────────────────────────────────────────────


def term_width() -> int:
    """Return current terminal column count (falls back to 80)."""
    return shutil.get_terminal_size((80, 24)).columns


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# ── Layout primitives ─────────────────────────────────────────────────────────


def rule(char: str = "─", colour: str = C.DIM) -> None:
    """Print a full-width horizontal rule."""
    print(f"{colour}{char * term_width()}{C.RESET}")


def header(title: str, subtitle: str = "") -> None:
    """Clear the screen and print a prominent page header."""
    clear()
    w = term_width()
    print(f"{C.BLUE}{C.BOLD}{'═' * w}{C.RESET}")
    print(f"{C.BLUE}{C.BOLD}  ◈  {title.upper()}{C.RESET}")
    if subtitle:
        print(f"{C.DIM}     {subtitle}{C.RESET}")
    print(f"{C.BLUE}{'─' * w}{C.RESET}")
    print()


def section(title: str) -> None:
    """Print a secondary section heading."""
    print(f"\n{C.CYAN}{C.BOLD}▸ {title}{C.RESET}")
    rule()


def success(msg: str) -> None:
    print(f"\n{C.GREEN}  ✔  {msg}{C.RESET}")


def error(msg: str) -> None:
    print(f"\n{C.RED}  ✘  {msg}{C.RESET}")


def warning(msg: str) -> None:
    print(f"\n{C.YELLOW}  ⚠  {msg}{C.RESET}")


def info(msg: str) -> None:
    print(f"{C.DIM}     {msg}{C.RESET}")


def blank() -> None:
    print()


# ── Input helpers ─────────────────────────────────────────────────────────────


def prompt(label: str, default: str = "") -> str:
    """Display a styled prompt and return the stripped input (or *default*)."""
    hint = f" [{default}]" if default else ""
    try:
        value = input(f"{C.CYAN}  ›  {label}{hint}: {C.RESET}").strip()
    except EOFError:
        return default
    return value if value else default


def prompt_int(
    label: str,
    valid: list[int] | None = None,
    allow_back: bool = True,
) -> int | None:
    """Prompt for an integer, restricted to *valid* when given.

    Returns ``None`` when the user enters ``0`` (back/cancel) and
    *allow_back* is ``True``.  Keeps looping on invalid input.
    """
    hint = "  (0 = zpět)" if allow_back else ""
    while True:
        raw = prompt(f"{label}{hint}")
        if allow_back and raw in ("0", ""):
            return None
        if not raw:
            continue
        try:
            value = int(raw)
        except ValueError:
            error(f"'{raw}' není platné číslo.")
            continue
        if valid is not None and value not in valid:
            ids_str = ", ".join(str(v) for v in valid[:10])
            suffix  = "…" if len(valid) > 10 else ""
            error(f"Neplatná volba {value}. Platné hodnoty: {ids_str}{suffix}")
            continue
        return value


def prompt_date(label: str) -> datetime:
    """Keep asking until the user enters a date in YYYY-MM-DD format."""
    while True:
        raw = prompt(f"{label} (RRRR-MM-DD)")
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            error("Neplatný formát data – zadejte ve tvaru RRRR-MM-DD (např. 2025-06-01).")


def pause() -> None:
    """Wait for the user to press Enter before continuing."""
    input(f"\n{C.DIM}  Stiskněte Enter pro pokračování…{C.RESET}")


def confirm(msg: str) -> bool:
    """Return ``True`` when the user confirms with *a/ano/y/yes*."""
    raw = prompt(f"{msg} [a/N]").lower()
    return raw in ("a", "ano", "y", "yes")


# ── Table renderer ────────────────────────────────────────────────────────────


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences so we can measure visible character width."""
    return re.sub(r"\033\[[0-9;]*m", "", s)


def _vlen(s: str) -> int:
    """Visible length of a string (ignores ANSI codes)."""
    return len(_strip_ansi(s))


def table(
    columns: list[str],
    rows: list[list[Any]],
    col_widths: list[int] | None = None,
) -> None:
    """Render a Unicode box-drawing table to stdout.

    *col_widths* is optional; when omitted the widths are computed from the
    content.  If the total width exceeds the terminal, the widest column is
    trimmed to fit.
    """
    if not rows:
        info("(žádné záznamy)")
        return

    str_rows: list[list[str]] = [[str(cell) for cell in row] for row in rows]

    if col_widths is None:
        col_widths = [
            max(_vlen(col), max((_vlen(r[i]) for r in str_rows), default=0))
            for i, col in enumerate(columns)
        ]

    # Clamp to terminal width
    total = sum(cw + 3 for cw in col_widths) + 1
    tw = term_width()
    if total > tw:
        excess = total - tw
        widest = col_widths.index(max(col_widths))
        col_widths[widest] = max(6, col_widths[widest] - excess)

    def _sep(l: str, m: str, r: str, f: str) -> str:
        return f"{C.DIM}{l}{m.join(f * (cw + 2) for cw in col_widths)}{r}{C.RESET}"

    def _row(cells: list[str], colour: str = "") -> str:
        parts = []
        for cell, cw in zip(cells, col_widths):
            vl = _vlen(cell)
            # Truncate if needed (rare – only when terminal is very narrow)
            visible = _strip_ansi(cell)
            if len(visible) > cw:
                cell = cell[: cw - 1] + "…"
                vl = cw
            pad = " " * (cw - vl)
            parts.append(f" {cell}{pad} ")
        return f"{colour}{C.DIM}│{C.RESET}{'│'.join(parts)}{C.DIM}│{C.RESET}"

    print(_sep("┌", "┬", "┐", "─"))
    print(_row(columns, C.BOLD + C.CYAN))
    print(_sep("├", "┼", "┤", "─"))
    for r in str_rows:
        print(_row(r))
    print(_sep("└", "┴", "┘", "─"))
