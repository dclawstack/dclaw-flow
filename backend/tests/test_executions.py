"""Tests for execution history: filters, retention, anomalies, SSE (P0.4)."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, NodeExecution, Workflow
from app.services.anomaly import detect_anomalies
from tests.conftest import test_engine


async def _make_workflow(db) -> uuid.UUID:
    wf = Workflow(name="WF", nodes=[], edges=[], trigger={})
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf.id


def _exec(wf_id, status="completed", started=None, completed=None, error=None):
    started = started or datetime.now(timezone.utc)
    return Execution(
        workflow_id=wf_id,
        status=status,
        trigger_source="manual",
        started_at=started,
        completed_at=completed,
        error=error,
    )


# --------------------------------------------------------------------------- #
# Anomaly heuristics (pure)
# --------------------------------------------------------------------------- #


def test_anomaly_flags_slow_run():
    wf = uuid.uuid4()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    history = [
        _exec(wf, started=base, completed=base + timedelta(seconds=1))
        for _ in range(5)
    ]
    slow = _exec(wf, started=base, completed=base + timedelta(seconds=30))
    slow.id = uuid.uuid4()
    flags = detect_anomalies(slow, history + [slow])
    assert any("Slow run" in f for f in flags)


def test_anomaly_flags_repeated_failures():
    wf = uuid.uuid4()
    history = [_exec(wf, status="failed") for _ in range(3)]
    current = _exec(wf, status="failed", error={"node_id": "a"})
    current.id = uuid.uuid4()
    flags = detect_anomalies(current, history + [current])
    assert any("Repeated failures" in f for f in flags)
    assert any("node 'a'" in f for f in flags)


def test_anomaly_clean_run_has_no_flags():
    wf = uuid.uuid4()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    history = [
        _exec(wf, started=base, completed=base + timedelta(seconds=1))
        for _ in range(5)
    ]
    normal = _exec(wf, started=base, completed=base + timedelta(seconds=1))
    normal.id = uuid.uuid4()
    assert detect_anomalies(normal, history + [normal]) == []


# --------------------------------------------------------------------------- #
# Query filters (API)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_filter_by_status_and_step(client):
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf_id = await _make_workflow(db)
        ok = _exec(wf_id, status="completed")
        bad = _exec(wf_id, status="failed")
        db.add_all([ok, bad])
        await db.commit()
        await db.refresh(bad)
        db.add(NodeExecution(execution_id=bad.id, node_id="step-x", status="failed"))
        await db.commit()

    by_status = await client.get("/api/v1/flows/executions?status=failed")
    assert by_status.status_code == 200
    items = by_status.json()["items"]
    assert items and all(e["status"] == "failed" for e in items)

    by_step = await client.get("/api/v1/flows/executions?node_id=step-x")
    ids = [e["id"] for e in by_step.json()["items"]]
    assert str(bad.id) in ids


@pytest.mark.asyncio
async def test_get_execution_includes_steps(client):
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf_id = await _make_workflow(db)
        ex = _exec(wf_id)
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        db.add(NodeExecution(execution_id=ex.id, node_id="n1", status="completed"))
        await db.commit()
        ex_id = ex.id

    resp = await client.get(f"/api/v1/flows/executions/{ex_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert [n["node_id"] for n in body["node_executions"]] == ["n1"]

    anomalies = await client.get(f"/api/v1/flows/executions/{ex_id}/anomalies")
    assert anomalies.status_code == 200
    assert "flags" in anomalies.json()


# --------------------------------------------------------------------------- #
# Retention + SSE
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_cleanup_requires_token_and_deletes_old(client):
    old = datetime.now(timezone.utc) - timedelta(days=120)
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf_id = await _make_workflow(db)
        db.add(_exec(wf_id, started=old, completed=old))
        db.add(_exec(wf_id))  # recent
        await db.commit()

    unauth = await client.post("/api/v1/flows/executions/admin/cleanup?days=90")
    assert unauth.status_code == 401

    ok = await client.post(
        "/api/v1/flows/executions/admin/cleanup?days=90",
        headers={"X-Admin-Token": "change-me-in-production"},
    )
    assert ok.status_code == 200
    assert ok.json()["deleted"] == 1  # only the 120-day-old one

    # days=0 means "everything" — must not fall back to the default window.
    purge_all = await client.post(
        "/api/v1/flows/executions/admin/cleanup?days=0",
        headers={"X-Admin-Token": "change-me-in-production"},
    )
    assert purge_all.json()["deleted"] == 1  # the recent one


@pytest.mark.asyncio
async def test_stream_emits_valid_json_and_terminates(client):
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf_id = await _make_workflow(db)
        ex = _exec(wf_id, status="completed")
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        db.add(NodeExecution(execution_id=ex.id, node_id="n1", status="completed"))
        await db.commit()
        ex_id = ex.id

    async with client.stream(
        "GET", f"/api/v1/flows/executions/{ex_id}/stream"
    ) as resp:
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk

    # Each SSE data line must be valid JSON, and the stream must terminate.
    assert "event: execution_completed" in body
    for line in body.splitlines():
        if line.startswith("data: "):
            json.loads(line[len("data: ") :])
