"""SQLite database connection, schema initialisation, and demo-data seeding."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from utils import hash_password

# Database file lives next to the implementace/ directory in a data/ folder
DB_PATH = Path(__file__).parent.parent / "data" / "pujcovna.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('student', 'admin')),
    password_hash TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL REFERENCES categories(id),
    name          TEXT    NOT NULL,
    manufacturer  TEXT    NOT NULL DEFAULT '',
    serial_number TEXT    NOT NULL UNIQUE,
    status        TEXT    NOT NULL DEFAULT 'Skladem'
                      CHECK (status IN ('Skladem','Rezervováno','Vypůjčeno','V opravě','Vyřazeno')),
    condition     TEXT    NOT NULL DEFAULT 'V pořádku',
    notes         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    item_id    INTEGER NOT NULL REFERENCES items(id),
    date_from  TEXT    NOT NULL,
    date_to    TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'Aktivní'
                   CHECK (status IN ('Aktivní','Expirovaná','Zrušená','Převedena')),
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER REFERENCES reservations(id),
    user_id        INTEGER NOT NULL REFERENCES users(id),
    item_id        INTEGER NOT NULL REFERENCES items(id),
    date_loaned    TEXT    NOT NULL,
    date_due       TEXT    NOT NULL,
    date_returned  TEXT,
    status         TEXT    NOT NULL DEFAULT 'Aktivní'
                       CHECK (status IN ('Aktivní','Ukončená')),
    notes          TEXT    NOT NULL DEFAULT ''
);
"""


class Database:
    """Manages the SQLite connection lifecycle.

    Usage::

        db = Database()
        db.connect()          # opens / creates the file, runs migrations
        ...
        db.close()
    """

    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the database, ensure the schema exists, seed demo data on first run."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self._path.exists()
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        if is_new:
            self._seed()

    def connection(self) -> sqlite3.Connection:
        """Return the active connection (raises if not yet connected)."""
        if self._conn is None:
            raise RuntimeError("Databáze není připojena – zavolejte nejprve connect().")
        return self._conn

    def close(self) -> None:
        """Close the connection gracefully."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Private helpers ───────────────────────────────────────────────────────

    def _seed(self) -> None:
        """Populate the fresh database with demo users, categories and items."""
        conn = self._conn
        now = datetime.now()

        # Users
        conn.executemany(
            "INSERT INTO users (username, full_name, email, role, password_hash) VALUES (?,?,?,?,?)",
            [
                ("admin",   "Administrátor",       "admin@fav.zcu.cz",        "admin",   hash_password("admin123")),
                ("jnovak",  "Jan Novák",            "jnovak@students.zcu.cz",  "student", hash_password("student1")),
                ("kprocko", "Kateřina Procházková", "kprocko@students.zcu.cz", "student", hash_password("student2")),
            ],
        )

        # Categories
        conn.executemany(
            "INSERT INTO categories (name, description) VALUES (?,?)",
            [
                ("Fotoaparát", "Digitální a filmové fotoaparáty"),
                ("Objektiv",   "Výměnné objektivy pro fotoaparáty"),
                ("Stativ",     "Stativy a gorillapody"),
                ("Osvětlení",  "Blesky, LED panely a příslušenství"),
                ("Zvuk",       "Mikrofony, rekordéry a sluchátka"),
            ],
        )

        # Items (category IDs match insertion order above: 1–5)
        conn.executemany(
            """INSERT INTO items (category_id, name, manufacturer, serial_number, status, condition)
               VALUES (?,?,?,?,?,?)""",
            [
                (1, "Canon EOS R50",          "Canon",      "CNR50-001",   "Skladem",  "V pořádku"),
                (1, "Canon EOS R50",          "Canon",      "CNR50-002",   "Skladem",  "Drobné škrábance na těle"),
                (1, "Sony α6400",             "Sony",       "SNA6400-001", "Skladem",  "V pořádku"),
                (1, "Nikon Z30",              "Nikon",      "NKZ30-001",   "V opravě", "Závada ostření – v servisu"),
                (2, "Canon RF 50 mm f/1.8",   "Canon",      "CNRF50-001",  "Skladem",  "V pořádku"),
                (2, "Sigma 16 mm f/1.4 DC DN","Sigma",      "SG16-001",    "Skladem",  "V pořádku"),
                (3, "Joby GorillaPod 3K",     "Joby",       "JB3K-001",    "Skladem",  "V pořádku"),
                (3, "Manfrotto MKCOMPACT",    "Manfrotto",  "MFCOMP-001",  "Skladem",  "V pořádku"),
                (4, "Godox TT685II",          "Godox",      "GX685-001",   "Skladem",  "V pořádku"),
                (5, "Rode VideoMicro II",     "Rode",       "RDEVM2-001",  "Skladem",  "V pořádku"),
            ],
        )

        # Demo reservation: jnovak reserved Canon RF for next week
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO reservations (user_id, item_id, date_from, date_to, status, created_at)
               VALUES (2, 5, ?, ?, 'Aktivní', ?)""",
            (tomorrow, next_week, now.isoformat()),
        )
        conn.execute("UPDATE items SET status='Rezervováno' WHERE id=5")

        # Demo loan: kprocko has the GorillaPod on loan
        conn.execute(
            """INSERT INTO loans (user_id, item_id, date_loaned, date_due, status)
               VALUES (3, 7, ?, ?, 'Aktivní')""",
            (now.strftime("%Y-%m-%d"), (now + timedelta(days=14)).strftime("%Y-%m-%d")),
        )
        conn.execute("UPDATE items SET status='Vypůjčeno' WHERE id=7")

        conn.commit()
