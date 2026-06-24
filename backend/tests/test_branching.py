"""Conditional branching in the execution engine (P1.3)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, NodeExecution, Workflow
from app.services.executor import execute_workflow
from tests.conftest import test_engine


def _node(node_id, ntype="action", **config):
    config.setdefault("action_type", "noop")  # avoid real HTTP
    return {"id": node_id, "type": ntype, "position": {"x": 0.0, "y": 0.0}, "config": config}


def _edge(source, target, condition=None):
    e = {"id": f"{source}->{target}", "source": source, "target": target}
    if condition is not None:
        e["condition"] = condition
    return e


async def _run(nodes, edges):
    """Run a workflow and return (execution_status, {node_id: status})."""
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
            select(NodeExecution).where(NodeExecution.execution_id == ex.id)
        )
        statuses = {ne.node_id: ne.status for ne in result.scalars().all()}
        return ex.status, statuses


@pytest.mark.asyncio
async def test_linear_flow_runs_all_nodes():
    nodes = [_node("t", "trigger"), _node("a"), _node("b")]
    edges = [_edge("t", "a"), _edge("a", "b")]
    status, ns = await _run(nodes, edges)
    assert status == "completed"
    assert ns == {"t": "completed", "a": "completed", "b": "completed"}


@pytest.mark.asyncio
async def test_true_branch_taken_false_skipped():
    nodes = [_node("t", "trigger"), _node("c", "conditional", expression="true"),
             _node("yes"), _node("no")]
    edges = [_edge("t", "c"),
             _edge("c", "yes", "{{c.result}}"),
             _edge("c", "no", "{{c.else}}")]
    status, ns = await _run(nodes, edges)
    assert status == "completed"
    assert ns["yes"] == "completed"
    assert ns["no"] == "skipped"


@pytest.mark.asyncio
async def test_false_branch_flips_selection():
    nodes = [_node("t", "trigger"), _node("c", "conditional", expression="false"),
             _node("yes"), _node("no")]
    edges = [_edge("t", "c"),
             _edge("c", "yes", "{{c.result}}"),
             _edge("c", "no", "{{c.else}}")]
    _, ns = await _run(nodes, edges)
    assert ns["yes"] == "skipped"
    assert ns["no"] == "completed"


@pytest.mark.asyncio
async def test_skip_propagates_downstream():
    nodes = [_node("t", "trigger"), _node("c", "conditional", expression="false"),
             _node("b"), _node("c2")]
    edges = [_edge("t", "c"),
             _edge("c", "b", "{{c.result}}"),  # not taken
             _edge("b", "c2")]                  # so c2 is unreachable too
    _, ns = await _run(nodes, edges)
    assert ns["b"] == "skipped"
    assert ns["c2"] == "skipped"


@pytest.mark.asyncio
async def test_or_convergence_runs_node_reached_by_any_active_path():
    nodes = [_node("t", "trigger"), _node("c", "conditional", expression="true"),
             _node("a"), _node("b"), _node("d")]
    edges = [_edge("t", "c"),
             _edge("c", "a", "{{c.result}}"),  # taken
             _edge("c", "b", "{{c.else}}"),    # skipped
             _edge("a", "d"), _edge("b", "d")]
    _, ns = await _run(nodes, edges)
    assert ns["a"] == "completed"
    assert ns["b"] == "skipped"
    assert ns["d"] == "completed"  # reached via the active 'a' path


@pytest.mark.asyncio
async def test_data_driven_edge_condition_on_upstream_output():
    # transform node emits {"flag": "yes"}; edges branch on its output.
    nodes = [_node("t", "trigger"),
             _node("x", "transform", mapping={"flag": "yes"}),
             _node("hit"), _node("miss")]
    edges = [_edge("t", "x"),
             _edge("x", "hit", "{{x.flag}}"),     # "yes" -> truthy
             _edge("x", "miss", "{{x.absent}}")]  # missing -> falsey
    _, ns = await _run(nodes, edges)
    assert ns["hit"] == "completed"
    assert ns["miss"] == "skipped"
