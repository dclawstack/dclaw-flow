"""Durable execution queue.

Executions live in the `executions` table as the queue. A claim is an atomic
`pending -> running` UPDATE that also sets a `locked_until` lease; whoever wins
the UPDATE runs the job, so the in-process worker and the API's fire-and-forget
task can never double-run one. On restart, jobs still `pending` are re-claimed
(durable); jobs left `running` are marked failed (at-most-once — the executor
fires real HTTP side effects, so we never silently re-run them).
"""

import asyncio
import contextlib
import uuid
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Execution, Workflow, now_utc
from app.observability import logger
from app.services.executor import execute_workflow


def _lease():
    return now_utc() + timedelta(seconds=settings.queue_lease_seconds)


async def _claim(db: AsyncSession, execution_id: uuid.UUID) -> bool:
    """Atomically move a pending, unleased execution to running. True if won."""
    result = await db.execute(
        update(Execution)
        .where(
            Execution.id == execution_id,
            Execution.status == "pending",
            or_(Execution.locked_until.is_(None), Execution.locked_until < now_utc()),
        )
        .values(
            status="running",
            attempts=Execution.attempts + 1,
            locked_until=_lease(),
        )
    )
    await db.commit()
    return result.rowcount == 1


async def _fail(db: AsyncSession, execution: Execution, message: str) -> None:
    execution.status = "failed"
    execution.error = {"message": message}
    execution.completed_at = now_utc()
    execution.locked_until = None
    await db.commit()


async def _run_claimed(execution_id: uuid.UUID) -> None:
    """Run an already-claimed (status=running) execution in a fresh session."""
    async with AsyncSessionLocal() as db:
        execution = await db.get(Execution, execution_id)
        if execution is None:
            return
        if execution.attempts > settings.queue_max_attempts:
            await _fail(db, execution, "Exceeded max queue attempts")
            logger.warning("execution_dead_letter", execution_id=str(execution_id))
            return
        workflow = await db.get(Workflow, execution.workflow_id)
        if workflow is None:
            await _fail(db, execution, "Workflow not found")
            return
        try:
            await execute_workflow(db, workflow, execution)
        finally:
            # The executor set the terminal status; release the lease.
            await db.execute(
                update(Execution)
                .where(Execution.id == execution_id)
                .values(locked_until=None)
            )
            await db.commit()


async def run_execution_durable(execution_id: uuid.UUID) -> None:
    """Claim then run. Used by the API/webhook fire-and-forget task and inline."""
    async with AsyncSessionLocal() as db:
        won = await _claim(db, execution_id)
    if won:
        await _run_claimed(execution_id)


async def drain_one() -> bool:
    """Claim and run the next pending job. True if one was processed."""
    async with AsyncSessionLocal() as db:
        execution_id = (
            await db.execute(
                select(Execution.id)
                .where(
                    Execution.status == "pending",
                    or_(
                        Execution.locked_until.is_(None),
                        Execution.locked_until < now_utc(),
                    ),
                )
                .order_by(Execution.started_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if execution_id is None:
            return False
        won = await _claim(db, execution_id)
    if won:
        await _run_claimed(execution_id)
    return True


async def recover_orphans() -> int:
    """Mark executions left running by a dead process as failed (at-most-once)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Execution)
            .where(Execution.status == "running")
            .values(
                status="failed",
                completed_at=now_utc(),
                locked_until=None,
                error={"message": "Interrupted by a worker restart"},
            )
        )
        await db.commit()
        return result.rowcount


async def worker_loop(stop: asyncio.Event) -> None:
    """Drain pending jobs until stopped; idle-poll when the queue is empty."""
    logger.info("queue_worker_started")
    while not stop.is_set():
        try:
            processed = await drain_one()
        except Exception:
            logger.exception("queue_worker_error")
            processed = False
        if not processed:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.queue_poll_seconds)
    logger.info("queue_worker_stopped")
