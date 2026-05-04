"""Authentication service – login and credential verification."""

from __future__ import annotations

from typing import Optional

from models.entities import User
from db.repositories import UserRepository
from utils import hash_password


class AuthService:
    """Handles user authentication against stored password hashes."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    def login(self, username: str, password: str) -> Optional[User]:
        """Return the :class:`User` if credentials are valid, otherwise ``None``."""
        user = self._repo.find_by_username(username.strip())
        if user is None:
            return None
        if user.password_hash == hash_password(password):
            return user
        return None
