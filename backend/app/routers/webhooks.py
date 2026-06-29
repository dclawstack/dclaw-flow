"""Webhook trigger router (P0.3)."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models import Execution, Workflow
from app.observability import WEBHOOK_INGEST, logger
from app.ratelimit import limiter, webhook_limit
from app.services.executor import execute_workflow
from app.services.schema_inference import infer_schema, validate_payload
from app.webhook_security import (
    is_replay,
    timestamp_within_tolerance,
    verify_signature,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _find_active_workflow(db: AsyncSession, webhook_id: str) -> Workflow | None:
    """Indexed lookup by webhook path (trigger #>> '{config,path}')."""
    stmt = select(Workflow).where(
        Workflow.status == "active",
        Workflow.trigger.op("->")("config").op("->>")("path") == webhook_id,
    )
    return (await db.execute(stmt)).scalars().first()


@router.post("/{webhook_id}", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(webhook_limit)
async def receive_webhook(
    webhook_id: str,
    request: Request,
    x_flow_signature: str | None = Header(default=None),
    x_flow_timestamp: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept an arbitrary JSON payload and trigger the matching workflow."""
    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        WEBHOOK_INGEST.labels("invalid_json").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from exc

    workflow = await _find_active_workflow(db, webhook_id)
    if not workflow:
        WEBHOOK_INGEST.labels("not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    config = workflow.trigger.get("config", {})
    secret = config.get("secret", "")
    if secret:
        # A timestamp opts the request into replay protection: it is folded into
        # the signed message, must be fresh, and the signature can't be reused.
        # Without one we fall back to body-only signing for backward compat —
        # unless the webhook is configured to require a timestamp.
        if x_flow_timestamp is not None:
            if not timestamp_within_tolerance(x_flow_timestamp):
                WEBHOOK_INGEST.labels("stale_timestamp").inc()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Timestamp outside tolerance window",
                )
            if not verify_signature(body, secret, x_flow_signature, x_flow_timestamp):
                WEBHOOK_INGEST.labels("unauthorized").inc()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )
            if is_replay(x_flow_signature or ""):
                WEBHOOK_INGEST.labels("replay").inc()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Replayed request",
                )
        else:
            if config.get("require_timestamp"):
                WEBHOOK_INGEST.labels("missing_timestamp").inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="X-Flow-Timestamp required",
                )
            if not verify_signature(body, secret, x_flow_signature):
                WEBHOOK_INGEST.labels("unauthorized").inc()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )

    # First payload teaches the schema; later payloads are validated against it.
    schema_errors: list[str] = []
    schema = config.get("inferred_schema")
    if schema is None:
        new_config = {**config, "inferred_schema": infer_schema(payload)}
        workflow.trigger = {**workflow.trigger, "config": new_config}
        await db.commit()
    else:
        schema_errors = validate_payload(payload, schema)
        if schema_errors:
            logger.info(
                "webhook_payload_mismatch",
                webhook_id=webhook_id,
                errors=schema_errors,
            )

    WEBHOOK_INGEST.labels("accepted").inc()

    execution = Execution(
        workflow_id=workflow.id,
        status="pending",
        trigger_source="webhook",
        trigger_payload=payload if isinstance(payload, dict) else {"_raw": payload},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    asyncio.create_task(run_webhook_execution(workflow, execution))

    return {
        "execution_id": str(execution.id),
        "status": "accepted",
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
    }


@router.get("/{webhook_id}/schema")
async def get_webhook_schema(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the inferred payload schema for a webhook (the auto-OpenAPI fragment)."""
    stmt = select(Workflow).where(
        Workflow.trigger.op("->")("config").op("->>")("path") == webhook_id,
    )
    workflow = (await db.execute(stmt)).scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    config = workflow.trigger.get("config", {})
    return {
        "webhook_id": webhook_id,
        "workflow_id": str(workflow.id),
        "schema": config.get("inferred_schema"),
    }


async def run_webhook_execution(workflow: Workflow, execution: Execution) -> None:
    async with AsyncSessionLocal() as session:
        await execute_workflow(session, workflow, execution)
