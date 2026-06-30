"""Token-based connectors: crypto, CRUD + isolation, execution (Phase 4)."""

import json

import pytest
from sqlalchemy import select

import app.connectors as connectors
from app.crypto import decrypt_json, encrypt_json
from app.database import AsyncSessionLocal
from app.models import NodeExecution

SLACK = {
    "name": "alerts",
    "connector_type": "slack_webhook",
    "secret": {"webhook_url": "https://hooks.slack.test/abc"},
}


def test_crypto_roundtrip_and_opaque():
    token = encrypt_json({"webhook_url": "https://hooks.slack.test/abc"})
    assert "hooks.slack" not in token  # ciphertext is opaque
    assert decrypt_json(token) == {"webhook_url": "https://hooks.slack.test/abc"}


@pytest.mark.asyncio
async def test_catalog_lists_connectors(client):
    r = await client.get("/api/v1/flows/connections/catalog")
    assert r.status_code == 200
    assert {"authenticated_http", "slack_webhook"} <= set(r.json())


@pytest.mark.asyncio
async def test_create_list_delete_never_leaks_secret(client):
    created = await client.post("/api/v1/flows/connections", json=SLACK)
    assert created.status_code == 201
    body = created.json()
    assert body["connector_type"] == "slack_webhook"
    assert "secret" not in body and "webhook_url" not in json.dumps(body)

    listed = await client.get("/api/v1/flows/connections")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "hooks.slack" not in json.dumps(listed.json())

    assert (
        await client.delete(f"/api/v1/flows/connections/{body['id']}")
    ).status_code == 204
    assert (await client.get("/api/v1/flows/connections")).json() == []


@pytest.mark.asyncio
async def test_unknown_connector_type_rejected(client):
    r = await client.post(
        "/api/v1/flows/connections",
        json={"name": "x", "connector_type": "nope", "secret": {}},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_connections_isolated_between_users(client, other_client):
    cid = (await client.post("/api/v1/flows/connections", json=SLACK)).json()["id"]
    assert (await other_client.get("/api/v1/flows/connections")).json() == []
    assert (
        await other_client.delete(f"/api/v1/flows/connections/{cid}")
    ).status_code == 404


@pytest.mark.asyncio
async def test_run_connector_slack(monkeypatch):
    captured = {}

    async def fake(url, method, headers, body):
        captured.update(url=url, method=method, body=body)
        return {"status": 200, "body": "ok"}

    monkeypatch.setattr(connectors, "http_request", fake)
    out = await connectors.run_connector(
        "slack_webhook", {"webhook_url": "https://hooks/x"}, {"text": "hi"}
    )
    assert out["status"] == 200
    assert captured["url"] == "https://hooks/x"
    assert captured["body"] == {"text": "hi"}


@pytest.mark.asyncio
async def test_run_connector_auth_http_injects_credentials(monkeypatch):
    captured = {}

    async def fake(url, method, headers, body):
        captured.update(headers=headers)
        return {"status": 200}

    monkeypatch.setattr(connectors, "http_request", fake)
    await connectors.run_connector(
        "authenticated_http",
        {"auth_type": "bearer", "token": "T"},
        {"url": "http://x", "method": "GET"},
    )
    assert captured["headers"]["Authorization"] == "Bearer T"

    await connectors.run_connector(
        "authenticated_http",
        {"auth_type": "api_key", "token": "K", "header_name": "X-Key"},
        {"url": "http://x", "method": "GET"},
    )
    assert captured["headers"]["X-Key"] == "K"


@pytest.mark.asyncio
async def test_connector_node_runs_and_secret_not_persisted(client, monkeypatch):
    captured = {}

    async def fake(url, method, headers, body):
        captured.update(url=url, body=body)
        return {"status": 200, "body": "ok"}

    monkeypatch.setattr(connectors, "http_request", fake)
    cid = (await client.post("/api/v1/flows/connections", json=SLACK)).json()["id"]
    wf = await client.post(
        "/api/v1/flows/workflows",
        json={
            "name": "C",
            "nodes": [
                {
                    "id": "t",
                    "type": "trigger",
                    "position": {"x": 0, "y": 0},
                    "config": {"trigger_type": "manual"},
                },
                {
                    "id": "n",
                    "type": "action",
                    "position": {"x": 1, "y": 0},
                    "config": {
                        "action_type": "connector",
                        "connection_id": cid,
                        "text": "hello",
                    },
                },
            ],
            "edges": [{"id": "e", "source": "t", "target": "n"}],
            "trigger": {"trigger_type": "manual", "config": {}},
        },
    )
    wid = wf.json()["id"]
    ex = await client.post(
        f"/api/v1/flows/workflows/{wid}/execute",
        json={"payload": {}, "wait_for_completion": True},
    )
    assert ex.json()["status"] == "completed"
    assert captured["url"] == "https://hooks.slack.test/abc"
    assert captured["body"] == {"text": "hello"}

    # The decrypted secret must never be persisted on the node execution input.
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(NodeExecution))).scalars().all()
        dumped = json.dumps([r.input for r in rows])
    assert "hooks.slack" not in dumped and "__connection" not in dumped
