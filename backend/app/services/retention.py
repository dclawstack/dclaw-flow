"""Execution history retention (P0.4)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution


async def delete_executions_older_than(db: AsyncSession, days: int) -> int:
    """Delete executions started more than `days` ago. Returns the count removed."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    count = await db.scalar(
        select(func.count())
        .select_from(Execution)
        .where(Execution.started_at < cutoff)
    )
    await db.execute(delete(Execution).where(Execution.started_at < cutoff))
    await db.commit()
    return count or 0
