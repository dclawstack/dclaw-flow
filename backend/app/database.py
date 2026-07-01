"""Database configuration and session management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import settings

# Under pytest (TESTING=1, set in conftest before import) use NullPool: each
# session opens a fresh connection bound to the current event loop and closes it
# on release. Pooling across pytest-asyncio's per-test loops otherwise leaves a
# connection bound to a dead loop, where a later await hangs forever. Production
# keeps the pooled, pre-pinged engine.
_testing = os.environ.get("TESTING") == "1"
_pool_kwargs = (
    {"poolclass": NullPool}
    if _testing
    # Neon (and other serverless Postgres) auto-suspends when idle and drops
    # connections; validate/recycle pooled connections so a dropped one
    # reconnects transparently instead of 500-ing the next request.
    else {"pool_pre_ping": True, "pool_recycle": 300}
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development" and not _testing,
    future=True,
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
