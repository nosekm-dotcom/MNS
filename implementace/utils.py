"""Shared utility helpers."""

import hashlib

_SALT = b"pujcovna_mns_2024"


def hash_password(password: str) -> str:
    """Return a PBKDF2-HMAC-SHA256 hex digest for the given plain-text password."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _SALT, 200_000).hex()
