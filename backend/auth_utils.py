"""
Password hashing and verification utilities.

Uses bcrypt for secure password storage (OWASP-recommended).
- bcrypt: industry standard, adaptive cost, salt included in hash
- 12 rounds: OWASP-recommended minimum for 2024+
- Constant-time verification to prevent timing attacks
"""

from __future__ import annotations

import bcrypt

# OWASP-recommended minimum cost factor (12 rounds = 2^12 iterations)
BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password for storage.

    Args:
        plain_password: User-supplied password (plaintext).

    Returns:
        Bcrypt hash string (includes salt, safe to store in DB).

    Security notes:
        - Never log or expose plain_password
        - bcrypt truncates passwords > 72 bytes (NUL-termination); consider
          pre-hashing with SHA-256 for very long passwords (not needed for typical use)
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Args:
        plain_password: User-supplied password (e.g. from login form).
        hashed_password: Stored hash from User.hashed_password.

    Returns:
        True if password matches, False otherwise.

    Security notes:
        - bcrypt.checkpw uses constant-time comparison
        - Invalid/malformed hashes raise ValueError; catch and return False
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False
