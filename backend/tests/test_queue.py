"""Durable execution queue: claim, drain, crash recovery, dead-letter (Phase 3)."""

import pytest
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import SYSTEM_USER_ID, Execution, Workflow
from app.services import queue

TRIGGER_ONLY = [
    {
        "id": "t",
        "type": "trigger",
        "position": {"x": 0, "y": 0},
        "config": {"trigger_type": "manual"},
    }
]


async def _make_execution(status="pending", attempts=0):
    async with AsyncSessionLocal() as db:
        wf = Workflow(
            name="Q",
            owner_id=SYSTEM_USER_ID,
            nodes=TRIGGER_ONLY,
            edges=[],
            trigger={"trigger_type": "manual", "config": {}},
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        ex = Execution(
            workflow_id=wf.id,
            status=status,
            attempts=attempts,
            trigger_source="manual",
            trigger_payload={},
        )
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        return ex.id


async def _status(execution_id):
    async with AsyncSessionLocal() as db:
        return await db.scalar(
            select(Execution.status).where(Execution.id == execution_id)
        )


@pytest.mark.asyncio
async def test_drain_one_runs_pending_to_terminal():
    eid = await _make_execution()
    assert await queue.drain_one() is True
    assert await _status(eid) == "completed"
    # Nothing left pending.
    assert await queue.drain_one() is False


@pytest.mark.asyncio
async def test_recover_orphans_marks_running_as_failed():
    eid = await _make_execution(status="running")
    recovered = await queue.recover_orphans()
    assert recovered >= 1
    assert await _status(eid) == "failed"


@pytest.mark.asyncio
async def test_claim_is_won_at_most_once():
    eid = await _make_execution()
    async with AsyncSessionLocal() as db1, AsyncSessionLocal() as db2:
        first = await queue._claim(db1, eid)
        second = await queue._claim(db2, eid)
    assert sorted([first, second]) == [False, True]
    assert await _status(eid) == "running"


@pytest.mark.asyncio
async def test_dead_letter_after_max_attempts():
    eid = await _make_execution(attempts=settings.queue_max_attempts)
    await queue.run_execution_durable(eid)  # claim bumps attempts past the max
    assert await _status(eid) == "failed"
