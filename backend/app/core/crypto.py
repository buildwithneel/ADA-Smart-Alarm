from __future__ import annotations

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger("ada.crypto")

_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    Returns a singleton Fernet cipher instance.
    Derives a consistent 32-byte base64-encoded key from TOKEN_ENCRYPTION_KEY or SECRET_KEY.
    """
    global _fernet_instance
    if _fernet_instance is None:
        raw_key = settings.TOKEN_ENCRYPTION_KEY or settings.SECRET_KEY
        # Deterministically derive 32 bytes via SHA256, then base64url encode for Fernet
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(key_hash)
        _fernet_instance = Fernet(fernet_key)
    return _fernet_instance


def encrypt_token(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypts a sensitive string (e.g., OAuth access/refresh token) at rest.
    Returns ciphertext as a utf-8 string. Returns None if plaintext is None.
    """
    if not plaintext:
        return None
    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Failed to encrypt sensitive token: {exc}")
        raise RuntimeError("Token encryption failure") from exc


def decrypt_token(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypts an encrypted token string.
    Returns plaintext string. Returns None if ciphertext is None.
    """
    if not ciphertext:
        return None
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.error("Token decryption failed: invalid or corrupted token")
        raise ValueError("Invalid or corrupted token") from exc
    except Exception as exc:
        logger.error(f"Unexpected token decryption failure: {exc}")
        raise RuntimeError("Token decryption failure") from exc
