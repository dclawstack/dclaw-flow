"""Observability endpoints: health, readiness, metrics (Phase 1)."""

import pytest


@pytest.mark.asyncio
async def test_health_is_liveness(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_checks_db(client):
    r = await client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "flow_http_requests_total" in body
    assert "flow_executions_total" in body
    assert "flow_webhook_ingest_total" in body


@pytest.mark.asyncio
async def test_requests_carry_a_request_id_header(client):
    r = await client.get("/health")
    assert r.headers.get("x-request-id")
