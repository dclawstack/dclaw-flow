"""In-process workflow execution engine."""

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, NodeExecution, Workflow
from app.services.engine import topological_sort


async def execute_workflow(
    db: AsyncSession,
    workflow: Workflow,
    execution: Execution,
) -> None:
    """Execute a workflow in-process using async topological sort."""
    execution.status = "running"
    execution.started_at = datetime.now(timezone.utc)
    await db.commit()

    nodes = workflow.nodes or []
    edges = workflow.edges or []
    node_map = {node["id"]: node for node in nodes}

    try:
        order = topological_sort(nodes, edges)
    except ValueError as e:
        execution.status = "failed"
        execution.error = {"message": str(e)}
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    outputs: dict[str, dict[str, Any]] = {}

    for node_id in order:
        node = node_map[node_id]
        node_exec = NodeExecution(
            execution_id=execution.id,
            node_id=node_id,
            status="running",
        )
        db.add(node_exec)
        await db.commit()

        try:
            node_input = build_node_input(node, outputs)
            node_exec.input = node_input
            await db.commit()

            output = await run_node(node, node_input)
            outputs[node_id] = output

            node_exec.status = "completed"
            node_exec.output = output
            await db.commit()
        except Exception as e:
            node_exec.status = "failed"
            node_exec.error = {"message": str(e)}
            await db.commit()
            execution.status = "failed"
            execution.error = {"node_id": node_id, "message": str(e)}
            execution.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

    execution.status = "completed"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()


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
        return {"result": "noop"}

    if node_type == "conditional":
        expression = config.get("expression", "true")
        return {"result": evaluate_expression(expression, node_input)}

    if node_type == "delay":
        duration = config.get("duration_seconds", 1)
        await asyncio.sleep(duration)
        return {"delayed": duration}

    if node_type == "transform":
        mapping = config.get("mapping", {})
        return apply_transform(mapping, node_input)

    return {"result": "noop"}


async def run_http_action(node_input: dict[str, Any]) -> dict[str, Any]:
    """Execute an HTTP request node."""
    url = node_input.get("url", "")
    method = node_input.get("method", "GET").upper()
    headers = node_input.get("headers", {})
    body = node_input.get("body")

    if not url:
        return {"status": 0, "error": "Missing URL"}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(
                    url,
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                )
            else:
                return {"status": 0, "error": f"Unsupported method: {method}"}
            return {
                "status": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
            }
        except httpx.RequestError as e:
            return {"status": 0, "error": str(e)}


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
