"""Level-based parallel execution + merge node (Phase 5D)."""

import asyncio

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import SYSTEM_USER_ID, Execution, NodeExecution, Workflow
from app.services import executor
from app.services.engine import topological_levels
from app.services.executor import execute_workflow


def _trigger(node_id="t"):
    return {
        "id": node_id,
        "type": "trigger",
        "position": {"x": 0, "y": 0},
        "config": {"trigger_type": "manual"},
    }


def _node(node_id, ntype, **config):
    return {
        "id": node_id,
        "type": ntype,
        "position": {"x": 0, "y": 0},
        "config": config,
    }


def _edge(src, tgt):
    return {"id": f"{src}-{tgt}", "source": src, "target": tgt}


async def _run(nodes, edges):
    async with AsyncSessionLocal() as db:
        wf = Workflow(
            name="P", owner_id=SYSTEM_USER_ID, nodes=nodes, edges=edges, trigger={}
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        ex = Execution(
            workflow_id=wf.id,
            status="pending",
            trigger_source="manual",
            trigger_payload={},
        )
        db.add(ex)
        await db.commit()
        await db.refresh(ex)
        await execute_workflow(db, wf, ex)
        await db.refresh(ex)
        rows = (
            await db.execute(
                select(NodeExecution).where(NodeExecution.execution_id == ex.id)
            )
        ).scalars().all()
        return ex, {r.node_id: r for r in rows}


def test_topological_levels_groups_independent_nodes():
    nodes = [
        _trigger("t"),
        _node("a", "delay"),
        _node("b", "delay"),
        _node("m", "merge"),
    ]
    edges = [_edge("t", "a"), _edge("t", "b"), _edge("a", "m"), _edge("b", "m")]
    levels = topological_levels(nodes, edges)
    assert levels == [["t"], ["a", "b"], ["m"]]


def test_levels_raise_on_cycle():
    nodes = [_node("a", "delay"), _node("b", "delay")]
    edges = [_edge("a", "b"), _edge("b", "a")]
    with pytest.raises(ValueError):
        topological_levels(nodes, edges)


@pytest.mark.asyncio
async def test_fanout_runs_both_branches_and_merge_combines():
    nodes = [
        _trigger("t"),
        _node("a", "delay", duration_seconds=0),
        _node("b", "delay", duration_seconds=0),
        _node("m", "merge", from_a="{{a.delayed}}", from_b="{{b.delayed}}"),
    ]
    edges = [_edge("t", "a"), _edge("t", "b"), _edge("a", "m"), _edge("b", "m")]
    ex, node_execs = await _run(nodes, edges)

    assert ex.status == "completed"
    assert node_execs["a"].status == "completed"
    assert node_execs["b"].status == "completed"
    # The merge node's output combines both branches' resolved outputs.
    assert node_execs["m"].output == {"from_a": "0", "from_b": "0"}


@pytest.mark.asyncio
async def test_independent_nodes_run_concurrently(monkeypatch):
    peak = 0
    running = 0

    async def counting(node, node_input):
        nonlocal peak, running
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.05)
        running -= 1
        return {"ok": True}

    monkeypatch.setattr(executor, "run_node", counting)
    nodes = [_trigger("t"), _node("a", "action"), _node("b", "action")]
    edges = [_edge("t", "a"), _edge("t", "b")]
    ex, _ = await _run(nodes, edges)

    assert ex.status == "completed"
    assert peak >= 2  # a and b executed at the same time
