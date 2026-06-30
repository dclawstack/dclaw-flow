"""Execution router (P0.4)."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Execution, NodeExecution, User, Workflow
from app.ownership import get_owned_execution
from app.schemas import ExecutionListResponse, ExecutionResponse
from app.services.anomaly import detect_anomalies
from app.services.copilot import analyze_failure
from app.services.retention import delete_executions_older_than

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    workflow_id: uuid.UUID | None = None,
    status: str | None = None,
    node_id: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List executions, filterable by workflow, status, date range, or step."""
    # Scope to executions of workflows the caller owns.
    conditions = [
        Execution.workflow_id.in_(
            select(Workflow.id).where(Workflow.owner_id == current_user.id)
        )
    ]
    if workflow_id:
        conditions.append(Execution.workflow_id == workflow_id)
    if status:
        conditions.append(Execution.status == status)
    if started_after:
        conditions.append(Execution.started_at >= started_after)
    if started_before:
        conditions.append(Execution.started_at <= started_before)
    if node_id:
        conditions.append(
            Execution.id.in_(
                select(NodeExecution.execution_id).where(
                    NodeExecution.node_id == node_id
                )
            )
        )

    query = select(Execution).where(*conditions)
    query = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(Execution).where(*conditions)
    )
    return {"items": executions, "total": total or 0}


@router.post("/admin/cleanup")
async def cleanup_executions(
    days: int | None = None,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Delete executions older than `days` (default = retention setting)."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )
    window = days if days is not None else settings.execution_retention_days
    removed = await delete_executions_older_than(db, window)
    return {"deleted": removed}


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Execution:
    return await get_owned_execution(db, execution_id, current_user)


@router.get("/{execution_id}/anomalies")
async def get_execution_anomalies(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Deterministic anomaly flags for an execution, vs its workflow's history."""
    execution = await get_owned_execution(db, execution_id, current_user)
    result = await db.execute(
        select(Execution)
        .where(Execution.workflow_id == execution.workflow_id)
        .order_by(Execution.started_at.desc())
        .limit(20)
    )
    history = list(result.scalars().all())
    return {"flags": detect_anomalies(execution, history)}


@router.get("/{execution_id}/root-cause")
async def get_execution_root_cause(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Plain-language 'why did this fail' (LLM with deterministic fallback)."""
    execution = await get_owned_execution(db, execution_id, current_user)
    if execution.status != "failed":
        return {"explanation": "No failure to analyze.", "source": "heuristic"}

    error = execution.error or {}
    workflow = await db.get(Workflow, execution.workflow_id)
    nodes = (workflow.nodes if workflow else None) or []
    node = next((n for n in nodes if n.get("id") == error.get("node_id")), {})
    explanation, source = await analyze_failure(
        error, node.get("type"), node.get("config", {})
    )
    return {"explanation": explanation, "source": source}


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Execution:
    execution = await get_owned_execution(db, execution_id, current_user)
    if execution.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution already finished",
        )
    execution.status = "cancelled"
    execution.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    await get_owned_execution(db, execution_id, current_user)

    async def event_generator() -> Any:
        seen: dict[str, str] = {}
        while True:
            result = await db.execute(
                select(NodeExecution)
                .where(NodeExecution.execution_id == execution_id)
                .order_by(NodeExecution.created_at),
            )
            for node in result.scalars().all():
                if seen.get(node.node_id) != node.status:
                    seen[node.node_id] = node.status
                    data = json.dumps({"node_id": node.node_id, "status": node.status})
                    yield f"event: node_update\ndata: {data}\n\n"

            # Re-read the live status (the earlier object is a stale snapshot).
            current = await db.scalar(
                select(Execution.status).where(Execution.id == execution_id)
            )
            if current in ("completed", "failed", "cancelled"):
                done = json.dumps({"status": current})
                yield f"event: execution_completed\ndata: {done}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
