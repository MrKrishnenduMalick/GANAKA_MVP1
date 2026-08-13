"""AES-256-GCM credential encryption (implementation/04 TOKEN_SECURITY)."""

import base64
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger("ganaka.crypto")

NONCE_LENGTH = 12
KEY_LENGTH = 32


class CryptoError(Exception):
    """Raised when credential encryption/decryption cannot be performed."""


def _load_key() -> bytes:
    """Decode and validate the AES-256 key from the environment."""
    raw = settings.ENCRYPTION_KEY or os.environ.get("ENCRYPTION_KEY", "")
    if not raw:
        raise CryptoError("ENCRYPTION_KEY is not configured.")
    try:
        key = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error):
        raise CryptoError("ENCRYPTION_KEY is not valid base64.")
    if len(key) != KEY_LENGTH:
        raise CryptoError(f"ENCRYPTION_KEY must decode to {KEY_LENGTH} bytes (AES-256).")
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a credential string and return base64(nonce || ciphertext)."""
    key = _load_key()
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(token: str) -> str:
    """Decrypt a value produced by :func:`encrypt`.

    Raises :class:`CryptoError` on invalid or tampered payloads.
    """
    key = _load_key()
    try:
        payload = base64.b64decode(token, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise CryptoError("Stored credential is not valid base64.") from exc
    if len(payload) <= NONCE_LENGTH:
        raise CryptoError("Stored credential is malformed.")
    nonce, ciphertext = payload[:NONCE_LENGTH], payload[NONCE_LENGTH:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag as exc:
        raise CryptoError("Stored credential failed authentication.") from exc
