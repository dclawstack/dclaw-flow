"""Owner-scoped dashboard stats endpoint (Phase 5, slice A)."""

import pytest

WF = {
    "name": "S",
    "nodes": [
        {
            "id": "t",
            "type": "trigger",
            "position": {"x": 0, "y": 0},
            "config": {"trigger_type": "manual"},
        }
    ],
    "edges": [],
    "trigger": {"trigger_type": "manual", "config": {}},
}


@pytest.mark.asyncio
async def test_stats_requires_auth(anon_client):
    assert (await anon_client.get("/api/v1/flows/executions/stats")).status_code == 401


@pytest.mark.asyncio
async def test_stats_reflects_owned_activity(client):
    # empty to start
    empty = (await client.get("/api/v1/flows/executions/stats")).json()
    assert empty["totals"]["workflows"] == 0
    assert empty["totals"]["executions"] == 0
    assert empty["success_rate"] is None

    wid = (await client.post("/api/v1/flows/workflows", json=WF)).json()["id"]
    await client.post(
        f"/api/v1/flows/workflows/{wid}/execute",
        json={"payload": {}, "wait_for_completion": True},
    )

    stats = (await client.get("/api/v1/flows/executions/stats")).json()
    assert stats["totals"]["workflows"] == 1
    assert stats["totals"]["executions"] == 1
    assert stats["by_status"].get("completed") == 1
    assert stats["success_rate"] == 1.0
    assert sum(d["count"] for d in stats["per_day"]) == 1


@pytest.mark.asyncio
async def test_stats_are_owner_scoped(client, other_client):
    wid = (await client.post("/api/v1/flows/workflows", json=WF)).json()["id"]
    await client.post(
        f"/api/v1/flows/workflows/{wid}/execute",
        json={"payload": {}, "wait_for_completion": True},
    )
    # The other user sees none of it.
    other = (await other_client.get("/api/v1/flows/executions/stats")).json()
    assert other["totals"]["workflows"] == 0
    assert other["totals"]["executions"] == 0
