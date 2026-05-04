"""Sdílené pomocné utility."""

import hashlib

_SALT = b"pujcovna_mns_2024"


def hash_password(password: str) -> str:
    """Vrátí hexadecimální PBKDF2-HMAC-SHA256 otisk zadaného hesla."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _SALT, 200_000).hex()
