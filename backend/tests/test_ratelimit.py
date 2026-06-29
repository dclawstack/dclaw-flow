"""Rate limiting (slowapi) on the public webhook ingest endpoint (Phase 1)."""

import pytest

from app.config import settings
from app.ratelimit import limiter


@pytest.mark.asyncio
async def test_webhook_ingest_is_rate_limited(client, monkeypatch):
    """The 3rd request within the window is rejected with 429.

    The limit is enforced before the route body, so an unknown webhook id is
    enough — the first two requests reach the 404, the third is throttled.
    """
    monkeypatch.setattr(settings, "webhook_rate_limit", "2/minute")
    limiter.enabled = True
    limiter.reset()

    r1 = await client.post("/api/v1/flows/webhooks/does-not-exist", json={})
    r2 = await client.post("/api/v1/flows/webhooks/does-not-exist", json={})
    r3 = await client.post("/api/v1/flows/webhooks/does-not-exist", json={})

    assert r1.status_code == 404
    assert r2.status_code == 404
    assert r3.status_code == 429
    assert r3.headers.get("Retry-After") == "60"


@pytest.mark.asyncio
async def test_rate_limit_disabled_lets_requests_through(client):
    """With the limiter disabled (suite default), bursts are not throttled."""
    for _ in range(5):
        r = await client.post("/api/v1/flows/webhooks/does-not-exist", json={})
        assert r.status_code == 404
