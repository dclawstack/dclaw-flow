"""Symmetric encryption for stored third-party credentials (Fernet).

A connection's secret blob is encrypted before it touches the database and only
decrypted at execution time. The key is derived from CONNECTIONS_SECRET_KEY, so
any string works as the configured secret.
"""

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.connections_secret_key.encode()).digest()
    )
    return Fernet(key)


def encrypt_json(data: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(token.encode()).decode())
