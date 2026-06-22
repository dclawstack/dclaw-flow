"""Tests for workflow graph helpers (validation, reachability)."""

from app.services.engine import find_unreachable_nodes


def _node(node_id: str, node_type: str = "action") -> dict:
    return {"id": node_id, "type": node_type, "config": {}}


def _edge(source: str, target: str) -> dict:
    return {"id": f"{source}-{target}", "source": source, "target": target}


def test_all_nodes_reachable_returns_empty():
    nodes = [_node("t", "trigger"), _node("a"), _node("b")]
    edges = [_edge("t", "a"), _edge("a", "b")]
    assert find_unreachable_nodes(nodes, edges) == []


def test_detects_disconnected_node():
    nodes = [_node("t", "trigger"), _node("a"), _node("orphan")]
    edges = [_edge("t", "a")]
    assert find_unreachable_nodes(nodes, edges) == ["orphan"]


def test_detects_node_only_reachable_backwards():
    # b -> a, but trigger only reaches a's... a has no outgoing, b unreachable
    nodes = [_node("t", "trigger"), _node("a"), _node("b")]
    edges = [_edge("t", "a"), _edge("b", "a")]
    assert find_unreachable_nodes(nodes, edges) == ["b"]


def test_no_trigger_returns_empty():
    nodes = [_node("a"), _node("b")]
    edges = [_edge("a", "b")]
    assert find_unreachable_nodes(nodes, edges) == []


def test_multiple_triggers_returns_empty():
    nodes = [_node("t1", "trigger"), _node("t2", "trigger"), _node("a")]
    edges = [_edge("t1", "a")]
    assert find_unreachable_nodes(nodes, edges) == []
