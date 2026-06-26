"""Failure alerts (P1.4)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, Workflow
from app.services import executor
from app.services.executor import _alert_payload, _send_alert, execute_workflow
from tests.conftest import test_engine


def _node(node_id, ntype="action"):
    return {
        "id": node_id,
        "type": ntype,
        "position": {"x": 0.0, "y": 0.0},
        "config": {"action_type": "noop"},
    }


def _edge(s, t, kind="normal"):
    return {"id": f"{s}->{t}", "source": s, "target": t, "kind": kind}


def _failing_run_node(fail_ids):
    async def fake(node, node_input):
        if node["type"] == "trigger":
            return {"triggered": True}
        if node["id"] in fail_ids:
            raise RuntimeError(f"boom {node['id']}")
        return {"ok": True}

    return fake


async def _run(nodes, edges):
    async with AsyncSession(test_engine, expire_on_commit=False) as db:
        wf = Workflow(name="WF", nodes=nodes, edges=edges, trigger={})
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        ex = Execution(workflow_id=wf.id, status="pending", trigger_source="manual")
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        await execute_workflow(db, wf, ex)
        await db.refresh(ex)
        return ex.status


# --------------------------------------------------------------------------- #
# When the alert fires
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_alert_fires_on_uncaught_failure(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    fired: list[dict] = []
    monkeypatch.setattr(executor, "_fire_alert", fired.append)
    status = await _run([_node("t", "trigger"), _node("a")], [_edge("t", "a")])
    assert status == "failed"
    assert len(fired) == 1
    p = fired[0]
    assert p["event"] == "workflow_failed"
    assert p["node_id"] == "a"
    assert "boom a" in p["error"]
    assert p["workflow_name"] == "WF"


@pytest.mark.asyncio
async def test_no_alert_on_success(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node(set()))
    fired: list[dict] = []
    monkeypatch.setattr(executor, "_fire_alert", fired.append)
    status = await _run([_node("t", "trigger"), _node("a")], [_edge("t", "a")])
    assert status == "completed"
    assert fired == []


@pytest.mark.asyncio
async def test_no_alert_on_caught_failure(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    fired: list[dict] = []
    monkeypatch.setattr(executor, "_fire_alert", fired.append)
    status = await _run(
        [_node("t", "trigger"), _node("a"), _node("rec")],
        [_edge("t", "a"), _edge("a", "rec", kind="error")],
    )
    assert status == "completed"
    assert fired == []  # recovered failure -> no alert


# --------------------------------------------------------------------------- #
# Payload + send
# --------------------------------------------------------------------------- #


def test_alert_payload_fields():
    wf = Workflow(id=uuid.uuid4(), name="My Flow", nodes=[], edges=[], trigger={})
    ex = Execution(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        status="failed",
        trigger_source="manual",
        error={"node_id": "x", "message": "oops", "attempts": 3},
    )
    p = _alert_payload(wf, ex)
    assert p["workflow_name"] == "My Flow"
    assert p["node_id"] == "x" and p["attempts"] == 3
    assert "My Flow" in p["text"] and "oops" in p["text"]


def test_fire_alert_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(executor.settings, "alert_webhook_url", "")
    executor._fire_alert({"text": "x"})  # no webhook -> no task, no error


class _FakeClient:
    posted: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None):
        _FakeClient.posted.append((url, json))


@pytest.mark.asyncio
async def test_send_alert_posts_when_configured(monkeypatch):
    _FakeClient.posted = []
    monkeypatch.setattr(executor.settings, "alert_webhook_url", "https://hook/abc")
    monkeypatch.setattr(executor.httpx, "AsyncClient", _FakeClient)
    await _send_alert({"text": "hello"})
    assert _FakeClient.posted == [("https://hook/abc", {"text": "hello"})]


@pytest.mark.asyncio
async def test_send_alert_swallows_errors(monkeypatch):
    class _BoomClient(_FakeClient):
        async def post(self, url, json=None):
            raise executor.httpx.ConnectError("nope")

    monkeypatch.setattr(executor.settings, "alert_webhook_url", "https://hook/abc")
    monkeypatch.setattr(executor.httpx, "AsyncClient", _BoomClient)
    await _send_alert({"text": "hello"})  # must not raise
