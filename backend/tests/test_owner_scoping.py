"""Auth enforcement + per-user owner isolation (Phase 2.3)."""

import pytest

WF_BODY = {
    "name": "Mine",
    "nodes": [
        {
            "id": "trigger-0",
            "type": "trigger",
            "position": {"x": 0, "y": 0},
            "config": {"trigger_type": "manual"},
        }
    ],
    "edges": [],
    "trigger": {"trigger_type": "manual", "config": {}},
}


@pytest.mark.asyncio
async def test_resource_routes_require_auth(anon_client):
    assert (await anon_client.get("/api/v1/flows/workflows")).status_code == 401
    assert (
        await anon_client.post("/api/v1/flows/workflows", json=WF_BODY)
    ).status_code == 401
    assert (await anon_client.get("/api/v1/flows/executions")).status_code == 401


@pytest.mark.asyncio
async def test_public_routes_stay_open(anon_client):
    assert (await anon_client.get("/health")).status_code == 200
    assert (
        await anon_client.get("/api/v1/flows/workflows/templates")
    ).status_code == 200


@pytest.mark.asyncio
async def test_workflows_are_isolated_between_users(client, other_client):
    created = await client.post("/api/v1/flows/workflows", json=WF_BODY)
    wid = created.json()["id"]

    # Owner sees it; the other user does not.
    assert (await client.get(f"/api/v1/flows/workflows/{wid}")).status_code == 200
    assert (
        await other_client.get(f"/api/v1/flows/workflows/{wid}")
    ).status_code == 404
    assert (await other_client.get("/api/v1/flows/workflows")).json()["total"] == 0

    # The other user can't mutate or delete it either.
    patch = await other_client.patch(
        f"/api/v1/flows/workflows/{wid}", json={"name": "Hijacked"}
    )
    assert patch.status_code == 404
    assert (
        await other_client.delete(f"/api/v1/flows/workflows/{wid}")
    ).status_code == 404


@pytest.mark.asyncio
async def test_executions_are_isolated_between_users(client, other_client):
    wid = (await client.post("/api/v1/flows/workflows", json=WF_BODY)).json()["id"]
    execution = await client.post(
        f"/api/v1/flows/workflows/{wid}/execute",
        json={"payload": {}, "wait_for_completion": True},
    )
    eid = execution.json()["id"]

    assert (await client.get(f"/api/v1/flows/executions/{eid}")).status_code == 200
    assert (
        await other_client.get(f"/api/v1/flows/executions/{eid}")
    ).status_code == 404
    assert (await other_client.get("/api/v1/flows/executions")).json()["total"] == 0
