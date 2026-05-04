"""Webhook trigger router."""

import asyncio
import hmac
import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models import Execution, Workflow
from app.schemas import WebhookPayload
from app.services.executor import execute_workflow

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def verify_signature(request: Request, secret: str) -> bool:
    body = await request.body()
    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    header = request.headers.get("X-Flow-Signature", "")
    expected = f"sha256={signature}"
    return hmac.compare_digest(expected, header)


@router.post("/{webhook_id}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    webhook_id: str,
    request: Request,
    payload: WebhookPayload,
    x_flow_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # For MVP, scan workflows to find matching webhook path
    result = await db.execute(select(Workflow).where(Workflow.status == "active"))
    workflows = result.scalars().all()

    workflow = None
    for wf in workflows:
        trigger_config = wf.trigger.get("config", {})
        if trigger_config.get("path") == webhook_id:
            workflow = wf
            break

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    secret = workflow.trigger.get("config", {}).get("secret", "")
    if secret and not await verify_signature(request, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    execution = Execution(
        workflow_id=workflow.id,
        status="pending",
        trigger_source="webhook",
        trigger_payload=payload.data or {},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    asyncio.create_task(run_webhook_execution(workflow, execution))

    return {"execution_id": str(execution.id), "status": "accepted"}


async def run_webhook_execution(workflow: Workflow, execution: Execution) -> None:
    async with AsyncSessionLocal() as session:
        await execute_workflow(session, workflow, execution)
