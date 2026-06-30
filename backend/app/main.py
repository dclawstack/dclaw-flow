"""FastAPI application entrypoint."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.observability import (
    ObservabilityMiddleware,
    configure_logging,
    logger,
    metrics_response,
)
from app.ratelimit import limiter
from app.routers import auth, copilot, executions, webhooks, workflows
from app.seed import seed_data
from app.services.queue import recover_orphans, worker_loop

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    for issue in settings.insecure_config_warnings():
        logger.warning("insecure_config", issue=issue)
    logger.info("startup", env=settings.app_env)

    worker_task: asyncio.Task | None = None
    stop = asyncio.Event()
    if settings.queue_worker_enabled:
        recovered = await recover_orphans()
        if recovered:
            logger.warning("executions_recovered_failed", count=recovered)
        worker_task = asyncio.create_task(worker_loop(stop))

    yield

    stop.set()
    if worker_task is not None:
        await worker_task
    await engine.dispose()


app = FastAPI(
    title="DClaw Flow API",
    description="Visual workflow automation platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return a 429 with a Retry-After hint when a client exceeds its limit."""
    return JSONResponse(
        {"detail": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
        headers={"Retry-After": "60"},
    )


app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/flows")
app.include_router(workflows.router, prefix="/api/v1/flows")
app.include_router(executions.router, prefix="/api/v1/flows")
app.include_router(webhooks.router, prefix="/api/v1/flows")
app.include_router(copilot.router, prefix="/api/v1/flows")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness — the process is up (used by the Render/Docker healthcheck)."""
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check() -> Response:
    """Readiness — verifies the database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception:
        logger.warning("readiness_db_unreachable")
        return JSONResponse({"status": "degraded"}, status_code=503)


@app.get("/metrics")
async def metrics() -> Response:
    return metrics_response()
