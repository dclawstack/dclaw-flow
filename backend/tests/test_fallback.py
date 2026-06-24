"""Fallback / error-path routing in the execution engine (P1.4 phase 2)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, NodeExecution, Workflow
from app.services import executor
from app.services.executor import execute_workflow
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


def _edge(source, target, kind="normal", condition=None):
    e = {
        "id": f"{source}->{target}:{kind}",
        "source": source,
        "target": target,
        "kind": kind,
    }
    if condition is not None:
        e["condition"] = condition
    return e


def _failing_run_node(fail_ids):
    """Fake run_node: nodes whose id is in fail_ids raise; others succeed."""

    async def fake(node, node_input):
        if node["type"] == "trigger":
            return {"triggered": True}
        if node["id"] in fail_ids:
            raise RuntimeError(f"fail {node['id']}")
        return {"ok": True}

    return fake


async def _noop_sleep(_seconds):
    return None


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
            .order_by(NodeExecution.node_id, NodeExecution.attempt_number)
        )
        return ex.status, list(result.scalars().all())


def _final(rows, node_id):
    matches = [r for r in rows if r.node_id == node_id]
    return matches[-1].status if matches else None


@pytest.mark.asyncio
async def test_error_path_recovers_execution(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    status, rows = await _run(
        [_node("t", "trigger"), _node("a"), _node("b")],
        [_edge("t", "a"), _edge("a", "b", kind="error")],
    )
    assert status == "completed"
    assert _final(rows, "a") == "failed"
    assert _final(rows, "b") == "completed"


@pytest.mark.asyncio
async def test_uncaught_failure_fails_execution(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    status, rows = await _run(
        [_node("t", "trigger"), _node("a"), _node("b")],
        [_edge("t", "a"), _edge("a", "b")],  # normal edge, no error path
    )
    assert status == "failed"
    assert _final(rows, "a") == "failed"
    # uncaught failure aborts immediately, so downstream nodes never run
    assert _final(rows, "b") is None


@pytest.mark.asyncio
async def test_error_edge_with_false_condition_is_not_caught(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    status, _ = await _run(
        [_node("t", "trigger"), _node("a"), _node("b")],
        [_edge("t", "a"), _edge("a", "b", kind="error", condition="{{a.missing}}")],
    )
    assert status == "failed"  # the only error edge can't fire


@pytest.mark.asyncio
async def test_error_edge_can_reference_failure(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    status, rows = await _run(
        [_node("t", "trigger"), _node("a"), _node("b")],
        # {{a.failed}} resolves truthy because a failed
        [_edge("t", "a"), _edge("a", "b", kind="error", condition="{{a.failed}}")],
    )
    assert status == "completed"
    assert _final(rows, "b") == "completed"


@pytest.mark.asyncio
async def test_recovery_node_failing_again_fails_execution(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a", "b"}))
    status, rows = await _run(
        [_node("t", "trigger"), _node("a"), _node("b"), _node("c")],
        [_edge("t", "a"), _edge("a", "b", kind="error"), _edge("b", "c", kind="error")],
    )
    # a fails -> b (recovery) fails -> c is its error path -> c runs and succeeds.
    assert status == "completed"
    assert _final(rows, "c") == "completed"


@pytest.mark.asyncio
async def test_success_does_not_fire_error_edge(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node(set()))  # nothing fails
    status, rows = await _run(
        [_node("t", "trigger"), _node("a"), _node("ok"), _node("err")],
        [_edge("t", "a"), _edge("a", "ok"), _edge("a", "err", kind="error")],
    )
    assert status == "completed"
    assert _final(rows, "ok") == "completed"
    assert _final(rows, "err") == "skipped"  # error edge never fires on success


@pytest.mark.asyncio
async def test_retries_then_error_route(monkeypatch):
    monkeypatch.setattr(executor, "run_node", _failing_run_node({"a"}))
    monkeypatch.setattr(executor.asyncio, "sleep", _noop_sleep)
    status, rows = await _run(
        [_node("t", "trigger"), _node("a", retry={"max_attempts": 2}), _node("b")],
        [_edge("t", "a"), _edge("a", "b", kind="error")],
    )
    assert status == "completed"
    a_rows = [r for r in rows if r.node_id == "a"]
    assert [r.attempt_number for r in a_rows] == [1, 2]
    assert all(r.status == "failed" for r in a_rows)
    assert _final(rows, "b") == "completed"
