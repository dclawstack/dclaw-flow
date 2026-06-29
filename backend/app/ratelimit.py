"""Rate limiting (slowapi, in-memory) for abuse-prone public endpoints."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


def webhook_limit() -> str:
    """Per-IP limit for the public webhook ingest endpoint."""
    return settings.webhook_rate_limit


def copilot_limit() -> str:
    """Per-IP limit for the (expensive) AI copilot endpoints."""
    return settings.copilot_rate_limit
