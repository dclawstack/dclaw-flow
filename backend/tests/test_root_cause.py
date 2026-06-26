"""AI root-cause analysis for failed steps (P1.4)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, Workflow
from app.services import copilot
from app.services.copilot import _heuristic_root_cause, analyze_failure
from tests.conftest import test_engine


def test_heuristic_patterns():
    assert "URL" in _heuristic_root_cause("Missing URL", {})
    assert "5xx" in _heuristic_root_cause("HTTP 503 from http://x", {"url": "http://x"})
    assert "reach" in _heuristic_root_cause(
        "HTTP request failed: All connection attempts failed", {"url": "http://x"}
    )
    assert "timed out" in _heuristic_root_cause("request timeout", {})
    assert "cycle" in _heuristic_root_cause("Workflow contains cycles", {}).lower()
    assert "step failed" in _heuristic_root_cause("weird error", {}).lower()


@pytest.mark.asyncio
async def test_analyze_failure_uses_heuristic_when_no_llm(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    explanation, source = await analyze_failure(
        {"message": "HTTP 500 from http://api", "attempts": 3},
        "action",
        {"url": "http://api"},
    )
    assert source == "heuristic"
    assert "5xx" in explanation


@pytest.mark.asyncio
async def test_root_cause_endpoint_for_failed_execution(client, monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf = Workflow(
            name="WF",
            nodes=[{"id": "a", "type": "action", "config": {"url": "http://x"}}],
            edges=[],
            trigger={},
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        ex = Execution(
            workflow_id=wf.id,
            status="failed",
            trigger_source="manual",
            error={
                "node_id": "a",
                "message": "HTTP request failed: refused",
                "attempts": 1,
            },
        )
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        ex_id = ex.id

    resp = await client.get(f"/api/v1/flows/executions/{ex_id}/root-cause")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "heuristic"
    assert "reach" in body["explanation"]


@pytest.mark.asyncio
async def test_root_cause_noop_for_non_failed(client):
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf = Workflow(name="WF", nodes=[], edges=[], trigger={})
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        ex = Execution(workflow_id=wf.id, status="completed", trigger_source="manual")
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        ex_id = ex.id

    resp = await client.get(f"/api/v1/flows/executions/{ex_id}/root-cause")
    assert resp.status_code == 200
    assert "No failure" in resp.json()["explanation"]
