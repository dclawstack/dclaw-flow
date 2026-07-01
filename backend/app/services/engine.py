"""Workflow validation and topological sorting."""

from collections import defaultdict
from typing import Any

from app.models import Workflow
from app.schemas import ValidationResponse


def validate_workflow(workflow: Workflow) -> ValidationResponse:
    """Validate a workflow structure."""
    errors: list[str] = []
    nodes = workflow.nodes or []
    edges = workflow.edges or []

    node_ids = {node["id"] for node in nodes}
    for edge in edges:
        if edge.get("source") not in node_ids:
            errors.append(f"Edge references unknown source: {edge.get('source')}")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge references unknown target: {edge.get('target')}")

    triggers = [node for node in nodes if node.get("type") == "trigger"]
    if len(triggers) == 0:
        errors.append("Workflow must have at least one trigger node")
    if len(triggers) > 1:
        errors.append("Workflow must have only one trigger node")

    try:
        topological_sort(nodes, edges)
    except ValueError as e:
        errors.append(str(e))

    return ValidationResponse(valid=len(errors) == 0, errors=errors)


def topological_sort(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str]:
    """Return node IDs in topological order."""
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {node["id"]: 0 for node in nodes}

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            graph[source].append(target)
            in_degree[target] += 1

    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    result: list[str] = []

    while queue:
        node_id = queue.pop(0)
        result.append(node_id)
        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(nodes):
        raise ValueError("Workflow contains cycles")

    return result


def topological_levels(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[list[str]]:
    """Group node IDs into dependency levels (Kahn's algorithm by rank).

    Nodes in the same level have no dependency between them and can run
    concurrently; every node's dependencies sit in strictly earlier levels.
    Flattening the levels yields a valid topological order. Raises on a cycle.
    """
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {node["id"]: 0 for node in nodes}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            graph[source].append(target)
            in_degree[target] += 1

    levels: list[list[str]] = []
    current = sorted(node_id for node_id, degree in in_degree.items() if degree == 0)
    seen = 0
    while current:
        levels.append(current)
        nxt: list[str] = []
        for node_id in current:
            seen += 1
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    nxt.append(neighbor)
        current = sorted(nxt)

    if seen != len(nodes):
        raise ValueError("Workflow contains cycles")

    return levels


def find_unreachable_nodes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str]:
    """Return node IDs not reachable from the single trigger via directed edges.

    Used for non-destructive "cleanup" hints. Returns an empty list when there
    is not exactly one trigger (entry point is undefined — validation reports
    that separately).
    """
    node_ids = {node["id"] for node in nodes}
    triggers = [node["id"] for node in nodes if node.get("type") == "trigger"]
    if len(triggers) != 1:
        return []

    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in node_ids and target in node_ids:
            graph[source].append(target)

    seen: set[str] = set()
    queue = [triggers[0]]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(graph[current])

    return [node_id for node_id in node_ids if node_id not in seen]
