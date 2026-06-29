"""Webhook signature verification and replay protection.

Signatures are HMAC-SHA256 over the raw body (``X-Flow-Signature: sha256=<hex>``).
When a sender also includes ``X-Flow-Timestamp`` (unix seconds), the timestamp is
folded into the signed message (``"<ts>.".encode() + body``) so it cannot be
tampered with, the timestamp must fall inside a tolerance window, and the
signature is remembered for the length of that window to reject replays.

The replay cache is in-memory — correct for the single-instance deployment. On
restart the cache clears, but the timestamp window still bounds any replay to a
few minutes.
"""

import hashlib
import hmac
import time

from app.config import settings

# signature -> expiry epoch (seconds)
_seen: dict[str, float] = {}


def _sign(body: bytes, secret: str, timestamp: str | None) -> str:
    message = body if timestamp is None else f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(
    body: bytes, secret: str, header: str | None, timestamp: str | None = None
) -> bool:
    """Constant-time check of ``X-Flow-Signature`` against the expected HMAC."""
    expected = f"sha256={_sign(body, secret, timestamp)}"
    return hmac.compare_digest(expected, header or "")


def timestamp_within_tolerance(timestamp: str, now: float | None = None) -> bool:
    """True if ``timestamp`` (unix seconds) is within the configured window."""
    current = time.time() if now is None else now
    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(current - ts) <= settings.webhook_timestamp_tolerance


def is_replay(signature: str, now: float | None = None) -> bool:
    """Record ``signature``; return True if it was already seen (a replay).

    Expired entries are swept opportunistically so the cache stays bounded.
    """
    current = time.time() if now is None else now
    for sig, expiry in list(_seen.items()):
        if expiry < current:
            del _seen[sig]
    if signature in _seen:
        return True
    _seen[signature] = current + settings.webhook_timestamp_tolerance
    return False
