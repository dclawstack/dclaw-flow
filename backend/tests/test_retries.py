"""Per-node retry policy in the execution engine (P1.4)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, NodeExecution, Workflow
from app.services import executor
from app.services.executor import execute_workflow, run_http_action
from tests.conftest import test_engine


def _node(node_id, ntype="action", retry=None, **config):
    node = {
        "id": node_id,
        "type": ntype,
        "position": {"x": 0.0, "y": 0.0},
        "config": config,
    }
    if retry is not None:
        node["retry"] = retry
    return node


def _edge(s, t):
    return {"id": f"{s}->{t}", "source": s, "target": t}


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

        result = await db.execute(
            select(NodeExecution)
            .where(NodeExecution.execution_id == ex.id)
            .order_by(NodeExecution.attempt_number)
        )
        return ex.status, list(result.scalars().all())


def _flaky_run_node(fail_until):
    """Fake run_node: the non-trigger node fails its first `fail_until` calls."""
    calls: dict[str, int] = {}

    async def fake(node, node_input):
        if node["type"] == "trigger":
            return {"triggered": True}
        nid = node["id"]
        calls[nid] = calls.get(nid, 0) + 1
        if calls[nid] <= fail_until:
            raise RuntimeError(f"boom {calls[nid]}")
        return {"ok": True}

    return fake


async def _noop_sleep(_seconds):
    return None


# --------------------------------------------------------------------------- #
# Retry loop
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _flaky_run_node(2))
    monkeypatch.setattr(executor.asyncio, "sleep", _noop_sleep)
    status, rows = await _run(
        [_node("t", "trigger"), _node("a", retry={"max_attempts": 3})],
        [_edge("t", "a")],
    )
    assert status == "completed"
    a = [r for r in rows if r.node_id == "a"]
    assert [r.attempt_number for r in a] == [1, 2, 3]
    assert [r.status for r in a] == ["failed", "failed", "completed"]


@pytest.mark.asyncio
async def test_retries_exhaust_fails_execution(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _flaky_run_node(99))
    monkeypatch.setattr(executor.asyncio, "sleep", _noop_sleep)
    status, rows = await _run(
        [_node("t", "trigger"), _node("a", retry={"max_attempts": 2})],
        [_edge("t", "a")],
    )
    assert status == "failed"
    a = [r for r in rows if r.node_id == "a"]
    assert len(a) == 2
    assert all(r.status == "failed" for r in a)


@pytest.mark.asyncio
async def test_no_retry_config_is_single_attempt(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _flaky_run_node(99))
    status, rows = await _run(
        [_node("t", "trigger"), _node("a")],
        [_edge("t", "a")],
    )
    assert status == "failed"
    a = [r for r in rows if r.node_id == "a"]
    assert len(a) == 1 and a[0].attempt_number == 1


@pytest.mark.asyncio
async def test_exponential_backoff_delays(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _flaky_run_node(99))
    delays: list[float] = []

    async def record_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(executor.asyncio, "sleep", record_sleep)
    await _run(
        [_node("t", "trigger"),
         _node("a", retry={"max_attempts": 4, "backoff_strategy": "exponential",
                           "backoff_seconds": 1})],
        [_edge("t", "a")],
    )
    # 3 waits between 4 attempts: 1, 2, 4 (no wait after the final attempt).
    assert delays == [1.0, 2.0, 4.0]


# --------------------------------------------------------------------------- #
# HTTP failure semantics (transport + 5xx retriable; 4xx flows through)
# --------------------------------------------------------------------------- #


class _FakeResp:
    def __init__(self, status):
        self.status_code = status
        self.text = "body"
        self.headers = {}


class _FakeClient:
    status = 200

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        return _FakeResp(_FakeClient.status)


@pytest.mark.asyncio
async def test_http_raises_on_5xx(monkeypatch):
    _FakeClient.status = 503
    monkeypatch.setattr(executor.httpx, "AsyncClient", _FakeClient)
    with pytest.raises(RuntimeError):
        await run_http_action({"url": "http://x", "method": "GET"})


@pytest.mark.asyncio
async def test_http_4xx_flows_through_as_output(monkeypatch):
    _FakeClient.status = 404
    monkeypatch.setattr(executor.httpx, "AsyncClient", _FakeClient)
    out = await run_http_action({"url": "http://x", "method": "GET"})
    assert out["status"] == 404


@pytest.mark.asyncio
async def test_http_raises_on_transport_error(monkeypatch):
    class _BoomClient(_FakeClient):
        async def get(self, url, headers=None):
            raise executor.httpx.ConnectError("connection refused")

    monkeypatch.setattr(executor.httpx, "AsyncClient", _BoomClient)
    with pytest.raises(RuntimeError):
        await run_http_action({"url": "http://x", "method": "GET"})
