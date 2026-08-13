"""Password hashing, JWT issuing/verification and opaque token helpers."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError

# A short deny-list of the most abused passwords. Kept in code (not secret data)
# so the check is deterministic and offline.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "qwerty123456",
    "administrator", "letmein123", "welcome123456", "iloveyou123",
    "qwertyuiop123", "1234567890123", "abcd1234abcd", "admin@123456",
    "password@123", "welcome@1234", "changeme123!", "ganaka@123456",
}

_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def validate_password_policy(password: str) -> None:
    """implementation/01_AUTHENTICATION.md PASSWORD_POLICY (12..128 chars)."""
    problems: list[str] = []
    if len(password) < 12:
        problems.append("Must be at least 12 characters long.")
    if len(password) > 128:
        problems.append("Must be at most 128 characters long.")
    if not re.search(r"[A-Z]", password):
        problems.append("Must contain an uppercase letter.")
    if not re.search(r"[a-z]", password):
        problems.append("Must contain a lowercase letter.")
    if not re.search(r"[0-9]", password):
        problems.append("Must contain a number.")
    if not _SPECIAL.search(password):
        problems.append("Must contain a special character.")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("This password is too common.")
    if problems:
        raise AppError("AUTH-010", details=[{"field": "password", "issue": p} for p in problems])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_opaque_token() -> str:
    """Single-use secret handed out over email / used as a refresh token."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Only the digest is persisted, so a DB read cannot replay a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    user_id: str,
    workspace_id: str | None,
    role: str | None,
    permissions: list[str],
    session_id: str,
) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)
    claims = {
        "sub": user_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "role": role,
        "permissions": permissions,
        "session_id": session_id,
        "issued_at": int(issued_at.timestamp()),
        "expires_at": int(expires_at.timestamp()),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "token_type": "access",
    }
    token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AppError("AUTH-002")
    except jwt.PyJWTError:
        raise AppError("AUTH-003")
    if claims.get("token_type") != "access":
        raise AppError("AUTH-003")
    return claims
