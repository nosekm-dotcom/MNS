"""Služba pro autentizaci, přihlášení a ověření přihlašovacích údajů."""

from __future__ import annotations

from typing import Optional

from models.entities import User
from db.repositories import UserRepository
from utils import hash_password


class AuthService:
    """Zajišťuje ověření uživatele vůči uloženým hashům hesel."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    def login(self, username: str, password: str) -> Optional[User]:
        """Vrátí :class:`User`, pokud jsou údaje platné, jinak ``None``."""
        user = self._repo.find_by_username(username.strip())
        if user is None:
            return None
        if user.password_hash == hash_password(password):
            return user
        return None
