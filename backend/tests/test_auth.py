"""Auth foundation: signup, login, current-user (Phase 2)."""

import pytest

from app.auth import hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong", h)


@pytest.mark.asyncio
async def test_signup_returns_token_and_user(anon_client):
    r = await anon_client.post(
        "/api/v1/flows/auth/signup",
        json={"email": "Alice@Example.com", "password": "supersecret"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"  # normalised to lowercase


@pytest.mark.asyncio
async def test_duplicate_email_rejected(anon_client):
    payload = {"email": "dupe@example.com", "password": "supersecret"}
    first = await anon_client.post("/api/v1/flows/auth/signup", json=payload)
    assert first.status_code == 201
    second = await anon_client.post("/api/v1/flows/auth/signup", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_short_password_rejected(anon_client):
    r = await anon_client.post(
        "/api/v1/flows/auth/signup",
        json={"email": "shorty@example.com", "password": "tiny"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_wrong_password(anon_client):
    await anon_client.post(
        "/api/v1/flows/auth/signup",
        json={"email": "bob@example.com", "password": "supersecret"},
    )
    ok = await anon_client.post(
        "/api/v1/flows/auth/login",
        json={"email": "bob@example.com", "password": "supersecret"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await anon_client.post(
        "/api/v1/flows/auth/login",
        json={"email": "bob@example.com", "password": "nope"},
    )
    assert bad.status_code == 401

    unknown = await anon_client.post(
        "/api/v1/flows/auth/login",
        json={"email": "ghost@example.com", "password": "whatever1"},
    )
    assert unknown.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_and_returns_user(anon_client):
    token = (
        await anon_client.post(
            "/api/v1/flows/auth/signup",
            json={"email": "carol@example.com", "password": "supersecret"},
        )
    ).json()["access_token"]

    me = await anon_client.get(
        "/api/v1/flows/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "carol@example.com"

    assert (await anon_client.get("/api/v1/flows/auth/me")).status_code == 401
    assert (
        await anon_client.get(
            "/api/v1/flows/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    ).status_code == 401
