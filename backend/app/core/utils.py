from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return naive UTC datetime for SQLAlchemy models."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
