"""In-process workflow execution engine."""

import asyncio
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors import run_connector
from app.crypto import decrypt_json
from app.database import AsyncSessionLocal
from app.models import Connection, Execution, NodeExecution, Workflow
from app.observability import EXECUTIONS, logger
from app.services.engine import topological_levels
from app.services.http_action import run_http_action

_alert_tasks: set[asyncio.Task[None]] = set()

# Bound concurrent node execution so a wide fan-out can't exhaust the DB pool.
_MAX_CONCURRENCY = 10


async def execute_workflow(
    db: AsyncSession,
    workflow: Workflow,
    execution: Execution,
) -> None:
    """Execute a workflow in topological order, following only active edges.

    A non-trigger node runs only if at least one incoming edge is active (its
    source ran and the edge's condition passes). Nodes on untaken branches are
    recorded as ``skipped``. Edges with no condition are always active, so
    linear flows behave exactly as before.
    """
    execution.status = "running"
    execution.started_at = datetime.now(timezone.utc)
    await db.commit()

    nodes = workflow.nodes or []
    edges = workflow.edges or []
    node_map = {node["id"]: node for node in nodes}

    try:
        levels = topological_levels(nodes, edges)
    except ValueError as e:
        execution.status = "failed"
        execution.error = {"message": str(e)}
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()
        EXECUTIONS.labels("failed").inc()
        return

    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        if edge.get("target"):
            incoming[edge["target"]].append(edge)

    outputs: dict[str, dict[str, Any]] = {}
    active: set[str] = set()
    failed: set[str] = set()
    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    for level in levels:
        # Independent nodes in a level run concurrently. Activation is decided
        # from earlier levels' state, so it's stable within the level; skipped
        # nodes are recorded on the shared session (sequential, no race).
        to_run: list[dict[str, Any]] = []
        for node_id in level:
            node = node_map[node_id]
            node_edges = incoming.get(node_id, [])
            is_entry = node.get("type") == "trigger"
            node_active = is_entry or any(
                _edge_active(edge, active, failed, outputs) for edge in node_edges
            )
            if not node_active:
                db.add(
                    NodeExecution(
                        execution_id=execution.id,
                        node_id=node_id,
                        status="skipped",
                    )
                )
                await db.commit()
            else:
                to_run.append(node)

        if not to_run:
            continue

        snapshot = dict(outputs)
        results = await asyncio.gather(
            *[
                _run_single_node(sem, node, snapshot, workflow, execution.id)
                for node in to_run
            ]
        )

        # Apply results in a stable order; fail-fast on the first uncaught error.
        for result in results:
            node_id = result["node_id"]
            outputs[node_id] = result["output"]
            if result["status"] == "completed":
                active.add(node_id)
                continue
            failed.add(node_id)
            error_edges = [
                e
                for e in edges
                if e.get("source") == node_id and e.get("kind") == "error"
            ]
            caught = any(_edge_active(e, active, failed, outputs) for e in error_edges)
            if not caught:
                execution.status = "failed"
                execution.error = {
                    "node_id": node_id,
                    "message": result["error"],
                    "attempts": result["attempts"],
                }
                execution.completed_at = datetime.now(timezone.utc)
                await db.commit()
                EXECUTIONS.labels("failed").inc()
                logger.info(
                    "execution_failed",
                    execution_id=str(execution.id),
                    node_id=node_id,
                    attempts=result["attempts"],
                )
                _fire_alert(_alert_payload(workflow, execution))
                return
            # Caught by an error/fallback path — continue with the next level.

    execution.status = "completed"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()
    EXECUTIONS.labels("completed").inc()


async def _run_single_node(
    sem: asyncio.Semaphore,
    node: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    workflow: Workflow,
    execution_id: uuid.UUID,
) -> dict[str, Any]:
    """Run one node (with its retry policy) in its own session so siblings can
    run concurrently. Returns {node_id, status, output, [error, attempts]}."""
    node_id = node["id"]
    policy = node.get("retry") or {}
    max_attempts = _retry_max(policy)
    last_error = ""

    async with sem, AsyncSessionLocal() as db:
        for attempt in range(1, max_attempts + 1):
            node_exec = NodeExecution(
                execution_id=execution_id,
                node_id=node_id,
                status="running",
                attempt_number=attempt,
            )
            db.add(node_exec)
            await db.commit()
            try:
                node_input = build_node_input(node, outputs)
                node_exec.input = node_input
                await db.commit()

                run_input = await _resolve_connection(
                    db, node, node_input, workflow.owner_id
                )
                output = await run_node(node, run_input)

                node_exec.status = "completed"
                node_exec.output = output
                await db.commit()
                return {"node_id": node_id, "status": "completed", "output": output}
            except Exception as e:
                last_error = str(e)
                node_exec.status = "failed"
                node_exec.error = {"message": last_error, "attempt": attempt}
                await db.commit()
                if attempt < max_attempts:
                    await asyncio.sleep(_backoff_delay(policy, attempt))

    return {
        "node_id": node_id,
        "status": "failed",
        "output": {"error": last_error, "failed": True, "attempts": max_attempts},
        "error": last_error,
        "attempts": max_attempts,
    }


def _edge_active(
    edge: dict[str, Any],
    active: set[str],
    failed: set[str],
    outputs: dict[str, dict[str, Any]],
) -> bool:
    """Is this edge active? Normal edges fire when the source succeeded; error
    edges fire when it failed. Either way the condition (if any) must be truthy.
    """
    source = edge.get("source")
    if edge.get("kind") == "error":
        if source not in failed:
            return False
    elif source not in active:
        return False
    condition = edge.get("condition")
    if not condition:
        return True
    return _is_truthy(resolve_template(condition, outputs))


def _is_truthy(value: str) -> bool:
    """Resolved-condition truthiness: empty / false-ish strings are falsey."""
    return value.strip().lower() not in ("", "false", "0", "no", "none", "null")


def _retry_max(policy: dict[str, Any]) -> int:
    """Clamp max_attempts to [1, 10] (a runaway-execution safety bound)."""
    return max(1, min(10, int(policy.get("max_attempts", 1))))


def _backoff_delay(policy: dict[str, Any], attempt: int) -> float:
    """Seconds to wait before the next attempt, per the backoff strategy."""
    strategy = policy.get("backoff_strategy", "none")
    base = float(policy.get("backoff_seconds", 1.0))
    if strategy == "fixed":
        return base
    if strategy == "exponential":
        return min(60.0, base * (2 ** (attempt - 1)))
    return 0.0


def _alert_payload(workflow: Workflow, execution: Execution) -> dict[str, Any]:
    """Build the failure-alert payload (Slack-compatible `text` + structured)."""
    err = execution.error or {}
    node_id = err.get("node_id")
    return {
        "text": (
            f"❌ Workflow '{workflow.name}' failed"
            f" at node '{node_id}': {err.get('message')}"
        ),
        "event": "workflow_failed",
        "workflow_id": str(workflow.id),
        "workflow_name": workflow.name,
        "execution_id": str(execution.id),
        "node_id": node_id,
        "error": err.get("message"),
        "attempts": err.get("attempts"),
        "failed_at": execution.completed_at.isoformat()
        if execution.completed_at
        else None,
    }


def _fire_alert(payload: dict[str, Any]) -> None:
    """Send the alert in the background; keep a ref so it isn't GC'd."""
    if not settings.alert_webhook_url:
        return
    task = asyncio.create_task(_send_alert(payload))
    _alert_tasks.add(task)
    task.add_done_callback(_alert_tasks.discard)


async def _send_alert(payload: dict[str, Any]) -> None:
    """POST the alert; never raise — a dead webhook must not affect runs."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(settings.alert_webhook_url, json=payload)
    except httpx.HTTPError as e:
        logger.warning("alert webhook failed: %s", e)


def build_node_input(
    node: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve variable templates in node config."""
    config = node.get("config", {})
    resolved: dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, str):
            resolved[key] = resolve_template(value, outputs)
        else:
            resolved[key] = value
    return resolved


def resolve_template(value: str, outputs: dict[str, dict[str, Any]]) -> str:
    """Replace {{ node_id.output_key }} with actual values."""
    pattern = r"\{\{\s*([\w\-]+)\.([\w\-]+)\s*\}\}"

    def replacer(match: re.Match[str]) -> str:
        node_id = match.group(1)
        output_key = match.group(2)
        node_output = outputs.get(node_id, {})
        result = node_output.get(output_key, "")
        return str(result)

    return re.sub(pattern, replacer, value)


async def run_node(
    node: dict[str, Any],
    node_input: dict[str, Any],
) -> dict[str, Any]:
    """Run a single node based on its type."""
    node_type = node.get("type")
    config = node.get("config", {})

    if node_type == "trigger":
        return {"triggered": True, "payload": node_input}

    if node_type == "action":
        action_type = config.get("action_type", "http")
        if action_type == "http":
            return await run_http_action(node_input)
        if action_type == "connector":
            connector_type, secret = node_input["__connection"]
            return await run_connector(connector_type, secret, node_input)
        return {"result": "noop"}

    if node_type == "conditional":
        expression = config.get("expression", "true")
        result = evaluate_expression(expression, node_input)
        # Expose both legs so edges can branch: {{cond.result}} / {{cond.else}}.
        return {"result": result, "else": not result}

    if node_type == "delay":
        duration = config.get("duration_seconds", 1)
        await asyncio.sleep(duration)
        return {"delayed": duration}

    if node_type == "transform":
        mapping = config.get("mapping", {})
        return apply_transform(mapping, node_input)

    if node_type == "merge":
        # A join point: its resolved config (with {{node.key}} refs to the
        # incoming branches) becomes the combined output. It runs after all
        # branches because topological levels place it in a later level.
        return node_input

    return {"result": "noop"}


async def _resolve_connection(
    db: AsyncSession,
    node: dict[str, Any],
    node_input: dict[str, Any],
    owner_id: uuid.UUID,
) -> dict[str, Any]:
    """For a connector action, decrypt its connection into a COPY of node_input.

    The secret is deliberately kept out of the persisted node_exec.input.
    """
    config = node.get("config", {})
    if node.get("type") != "action" or config.get("action_type") != "connector":
        return node_input
    try:
        connection_id = uuid.UUID(str(config.get("connection_id")))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Connection not found") from exc
    connection = await db.get(Connection, connection_id)
    if connection is None or connection.owner_id != owner_id:
        raise RuntimeError("Connection not found")
    secret = decrypt_json(connection.encrypted_secret)
    return {**node_input, "__connection": (connection.connector_type, secret)}


def evaluate_expression(expression: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a simple boolean expression."""
    # Very basic MVP evaluator — replace with a proper engine later
    if expression.lower() in ("true", "1", "yes"):
        return True
    if expression.lower() in ("false", "0", "no"):
        return False
    # Simple key existence check
    if expression.startswith("$"):
        key = expression[1:]
        return key in context and bool(context[key])
    return False


def apply_transform(
    mapping: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Apply a JSON transform mapping."""
    result: dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, str) and value.startswith("$"):
            result[key] = context.get(value[1:])
        else:
            result[key] = value
    return result
