import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import SYSTEM_USER_ID, User
from app.ratelimit import limiter

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/dclaw_app_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


async def override_get_db():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # System user so direct Workflow() inserts (engine tests) satisfy the owner FK.
    async with AsyncSession(test_engine, expire_on_commit=False) as s:
        s.add(User(id=SYSTEM_USER_ID, email="system@example.com", hashed_password="!"))
        await s.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
def reset_limiter():
    """Disable rate limiting by default so it can't flake the suite; the
    dedicated rate-limit test re-enables it explicitly."""
    limiter.enabled = False
    limiter.reset()
    yield
    limiter.reset()


async def _signup(ac, email):
    r = await ac.post(
        "/api/v1/flows/auth/signup",
        json={"email": email, "password": "supersecret"},
    )
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated client (for auth tests and 401 checks)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client():
    """Authenticated client, acting as the system user — the default owner for
    direct Workflow() inserts, so engine tests stay reachable through the API."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        token = create_access_token(
            User(id=SYSTEM_USER_ID, email="system@example.com")
        )
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest_asyncio.fixture
async def other_client():
    """A second authenticated user, for owner-isolation tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        token = await _signup(ac, "other@example.com")
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac
