"""API tests for workflow CRUD — focus on the canvas save round-trip (P0.2)."""

import pytest

TRIGGER = {
    "id": "trigger-0",
    "type": "trigger",
    "position": {"x": 100.0, "y": 150.0},
    "config": {"trigger_type": "manual"},
}
ACTION = {
    "id": "action-1",
    "type": "action",
    "position": {"x": 300.0, "y": 150.0},
    "config": {},
}


@pytest.mark.asyncio
async def test_patch_persists_nodes_edges_and_positions(client):
    create = await client.post(
        "/api/v1/flows/workflows",
        json={"name": "Canvas", "nodes": [TRIGGER], "edges": []},
    )
    assert create.status_code == 201
    wid = create.json()["id"]

    moved = {**ACTION, "position": {"x": 555.0, "y": 420.0}}
    resp = await client.patch(
        f"/api/v1/flows/workflows/{wid}",
        json={
            "nodes": [TRIGGER, moved],
            "edges": [{"id": "e1", "source": "trigger-0", "target": "action-1"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) == 2
    assert len(body["edges"]) == 1
    saved_action = next(n for n in body["nodes"] if n["id"] == "action-1")
    assert saved_action["position"] == {"x": 555.0, "y": 420.0}

    # Positions survive a reload.
    got = await client.get(f"/api/v1/flows/workflows/{wid}")
    reloaded = next(n for n in got.json()["nodes"] if n["id"] == "action-1")
    assert reloaded["position"] == {"x": 555.0, "y": 420.0}


@pytest.mark.asyncio
async def test_patch_node_deletion_round_trips(client):
    create = await client.post(
        "/api/v1/flows/workflows",
        json={
            "name": "Del",
            "nodes": [TRIGGER, ACTION],
            "edges": [{"id": "e1", "source": "trigger-0", "target": "action-1"}],
        },
    )
    wid = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/flows/workflows/{wid}",
        json={"nodes": [TRIGGER], "edges": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [n["id"] for n in body["nodes"]] == ["trigger-0"]
    assert body["edges"] == []


@pytest.mark.asyncio
async def test_patch_metadata_only_leaves_graph_untouched(client):
    create = await client.post(
        "/api/v1/flows/workflows",
        json={"name": "Meta", "nodes": [TRIGGER, ACTION], "edges": []},
    )
    wid = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/flows/workflows/{wid}",
        json={"status": "active"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "active"
    assert len(body["nodes"]) == 2  # graph not clobbered by unset fields
