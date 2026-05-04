"""Data-access layer – Repository pattern.

Each repository encapsulates all SQL queries for one aggregate root, so
the rest of the application never touches raw SQL.  The pattern makes it
trivial to swap the storage backend (e.g. replace SQLite with PostgreSQL)
without touching service or UI code.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from models.entities import Category, Item, Loan, Reservation, User
from db.database import Database


def _dt(value: str | None) -> Optional[datetime]:
    """Parse an ISO-8601 string to datetime; return None for NULL."""
    return datetime.fromisoformat(value) if value else None


# ── Base ──────────────────────────────────────────────────────────────────────


class _Repo:
    """Thin base that gives subclasses easy access to the connection."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection()


# ── User ──────────────────────────────────────────────────────────────────────


class UserRepository(_Repo):
    """Repository for :class:`~models.entities.User` persistence."""

    def find_by_username(self, username: str) -> Optional[User]:
        """Return the user with *username*, or ``None`` if not found."""
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return self._map(row) if row else None

    def find_by_id(self, user_id: int) -> Optional[User]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return self._map(row) if row else None

    def find_students(self) -> list[User]:
        rows = self._conn.execute(
            "SELECT * FROM users WHERE role = 'student' ORDER BY full_name"
        ).fetchall()
        return [self._map(r) for r in rows]

    @staticmethod
    def _map(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            email=row["email"],
            role=row["role"],
            password_hash=row["password_hash"],
        )


# ── Category ──────────────────────────────────────────────────────────────────


class CategoryRepository(_Repo):
    """Repository for :class:`~models.entities.Category` persistence."""

    def find_all(self) -> list[Category]:
        rows = self._conn.execute(
            "SELECT * FROM categories ORDER BY name"
        ).fetchall()
        return [Category(id=r["id"], name=r["name"], description=r["description"]) for r in rows]

    def find_by_id(self, cat_id: int) -> Optional[Category]:
        row = self._conn.execute(
            "SELECT * FROM categories WHERE id = ?", (cat_id,)
        ).fetchone()
        return Category(id=row["id"], name=row["name"], description=row["description"]) if row else None


# ── Item ──────────────────────────────────────────────────────────────────────

_ITEM_SELECT = """
    SELECT i.*, c.name AS category_name
    FROM   items i
    JOIN   categories c ON c.id = i.category_id
"""


class ItemRepository(_Repo):
    """Repository for :class:`~models.entities.Item` persistence."""

    def find_all(self, include_retired: bool = False) -> list[Item]:
        """Return all items, optionally excluding retired ones."""
        where = "" if include_retired else " WHERE i.status != 'Vyřazeno'"
        rows = self._conn.execute(
            f"{_ITEM_SELECT}{where} ORDER BY c.name, i.name"
        ).fetchall()
        return [self._map(r) for r in rows]

    def find_by_id(self, item_id: int) -> Optional[Item]:
        row = self._conn.execute(
            f"{_ITEM_SELECT} WHERE i.id = ?", (item_id,)
        ).fetchone()
        return self._map(row) if row else None

    def update_status(self, item_id: int, status: str) -> None:
        """Change only the status field of an item."""
        self._conn.execute(
            "UPDATE items SET status = ? WHERE id = ?", (status, item_id)
        )
        self._conn.commit()

    def update_status_and_condition(self, item_id: int, status: str, condition: str) -> None:
        """UC16 – update both status and condition (after return or admin review)."""
        self._conn.execute(
            "UPDATE items SET status = ?, condition = ? WHERE id = ?",
            (status, condition, item_id),
        )
        self._conn.commit()

    @staticmethod
    def _map(row: sqlite3.Row) -> Item:
        return Item(
            id=row["id"],
            category_id=row["category_id"],
            name=row["name"],
            manufacturer=row["manufacturer"],
            serial_number=row["serial_number"],
            status=row["status"],
            condition=row["condition"],
            notes=row["notes"],
            category_name=row["category_name"],
        )


# ── Reservation ───────────────────────────────────────────────────────────────

_RES_SELECT = """
    SELECT r.*,
           u.full_name     AS user_name,
           i.name          AS item_name,
           i.serial_number AS item_serial
    FROM   reservations r
    JOIN   users u ON u.id = r.user_id
    JOIN   items i ON i.id = r.item_id
"""


class ReservationRepository(_Repo):
    """Repository for :class:`~models.entities.Reservation` persistence."""

    def create(
        self,
        user_id: int,
        item_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> Reservation:
        """Insert a new *Aktivní* reservation and return the persisted object."""
        now = datetime.now().isoformat()
        cur = self._conn.execute(
            """INSERT INTO reservations (user_id, item_id, date_from, date_to, status, created_at)
               VALUES (?, ?, ?, ?, 'Aktivní', ?)""",
            (user_id, item_id, date_from.isoformat(), date_to.isoformat(), now),
        )
        self._conn.commit()
        return self.find_by_id(cur.lastrowid)  # type: ignore[return-value]

    def find_by_id(self, res_id: int) -> Optional[Reservation]:
        row = self._conn.execute(
            f"{_RES_SELECT} WHERE r.id = ?", (res_id,)
        ).fetchone()
        return self._map(row) if row else None

    def find_active_for_user(self, user_id: int) -> list[Reservation]:
        rows = self._conn.execute(
            f"{_RES_SELECT} WHERE r.user_id = ? AND r.status = 'Aktivní' ORDER BY r.date_from",
            (user_id,),
        ).fetchall()
        return [self._map(r) for r in rows]

    def find_all_active(self) -> list[Reservation]:
        rows = self._conn.execute(
            f"{_RES_SELECT} WHERE r.status = 'Aktivní' ORDER BY r.date_from"
        ).fetchall()
        return [self._map(r) for r in rows]

    def find_expired_candidates(self, cutoff: datetime) -> list[Reservation]:
        """Return active reservations whose pickup window has passed *cutoff* (UC09)."""
        rows = self._conn.execute(
            f"{_RES_SELECT} WHERE r.status = 'Aktivní' AND r.date_from < ?",
            (cutoff.isoformat(),),
        ).fetchall()
        return [self._map(r) for r in rows]

    def update_status(self, res_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE reservations SET status = ? WHERE id = ?", (status, res_id)
        )
        self._conn.commit()

    @staticmethod
    def _map(row: sqlite3.Row) -> Reservation:
        return Reservation(
            id=row["id"],
            user_id=row["user_id"],
            item_id=row["item_id"],
            date_from=datetime.fromisoformat(row["date_from"]),
            date_to=datetime.fromisoformat(row["date_to"]),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            user_name=row["user_name"],
            item_name=row["item_name"],
            item_serial=row["item_serial"],
        )


# ── Loan ──────────────────────────────────────────────────────────────────────

_LOAN_SELECT = """
    SELECT l.*,
           u.full_name     AS user_name,
           i.name          AS item_name,
           i.serial_number AS item_serial
    FROM   loans l
    JOIN   users u ON u.id = l.user_id
    JOIN   items i ON i.id = l.item_id
"""


class LoanRepository(_Repo):
    """Repository for :class:`~models.entities.Loan` persistence."""

    def create(
        self,
        user_id: int,
        item_id: int,
        date_due: datetime,
        reservation_id: Optional[int] = None,
        notes: str = "",
    ) -> Loan:
        """Insert a new *Aktivní* loan and return the persisted object."""
        now = datetime.now().isoformat()
        cur = self._conn.execute(
            """INSERT INTO loans
                   (reservation_id, user_id, item_id, date_loaned, date_due, status, notes)
               VALUES (?, ?, ?, ?, ?, 'Aktivní', ?)""",
            (reservation_id, user_id, item_id, now, date_due.isoformat(), notes),
        )
        self._conn.commit()
        return self.find_by_id(cur.lastrowid)  # type: ignore[return-value]

    def find_by_id(self, loan_id: int) -> Optional[Loan]:
        row = self._conn.execute(
            f"{_LOAN_SELECT} WHERE l.id = ?", (loan_id,)
        ).fetchone()
        return self._map(row) if row else None

    def find_active_loans(self) -> list[Loan]:
        rows = self._conn.execute(
            f"{_LOAN_SELECT} WHERE l.status = 'Aktivní' ORDER BY l.date_due"
        ).fetchall()
        return [self._map(r) for r in rows]

    def find_active_for_item(self, item_id: int) -> Optional[Loan]:
        row = self._conn.execute(
            f"{_LOAN_SELECT} WHERE l.item_id = ? AND l.status = 'Aktivní'", (item_id,)
        ).fetchone()
        return self._map(row) if row else None

    def close_loan(self, loan_id: int) -> None:
        """Mark a loan as *Ukončená* and record the return timestamp."""
        now = datetime.now().isoformat()
        self._conn.execute(
            "UPDATE loans SET status = 'Ukončená', date_returned = ? WHERE id = ?",
            (now, loan_id),
        )
        self._conn.commit()

    @staticmethod
    def _map(row: sqlite3.Row) -> Loan:
        return Loan(
            id=row["id"],
            reservation_id=row["reservation_id"],
            user_id=row["user_id"],
            item_id=row["item_id"],
            date_loaned=datetime.fromisoformat(row["date_loaned"]),
            date_due=datetime.fromisoformat(row["date_due"]),
            date_returned=_dt(row["date_returned"]),
            status=row["status"],
            notes=row["notes"],
            user_name=row["user_name"],
            item_name=row["item_name"],
            item_serial=row["item_serial"],
        )
