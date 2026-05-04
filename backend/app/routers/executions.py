"""Execution router."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models import Execution, NodeExecution, Workflow
from app.schemas import ExecutionCreate, ExecutionListResponse, ExecutionResponse
from app.services.executor import execute_workflow

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow_endpoint(
    workflow_id: uuid.UUID,
    data: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
) -> Execution:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    execution = Execution(
        workflow_id=workflow_id,
        status="pending",
        trigger_source="manual",
        trigger_payload=data.payload,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    if data.wait_for_completion:
        await execute_workflow(db, workflow, execution)
        await db.refresh(execution)
    else:
        asyncio.create_task(run_execution(workflow, execution))

    return execution


async def run_execution(workflow: Workflow, execution: Execution) -> None:
    """Run execution in background with a fresh session."""
    async with AsyncSessionLocal() as session:
        await execute_workflow(session, workflow, execution)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Execution:
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
    return execution


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    workflow_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(Execution)
    if workflow_id:
        query = query.where(Execution.workflow_id == workflow_id)
    query = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()

    count_query = select(func.count()).select_from(Execution)
    if workflow_id:
        count_query = count_query.where(Execution.workflow_id == workflow_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    return {"items": executions, "total": total}


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Execution:
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
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
) -> StreamingResponse:
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    async def event_generator() -> Any:
        while True:
            result = await db.execute(
                select(NodeExecution)
                .where(NodeExecution.execution_id == execution_id)
                .order_by(NodeExecution.created_at),
            )
            nodes = result.scalars().all()
            for node in nodes:
                payload = {"node_id": node.node_id, "status": node.status}
                yield f"event: node_update\ndata: {payload}\n\n"

            if execution.status in ("completed", "failed", "cancelled"):
                payload = {"status": execution.status}
                yield f"event: execution_completed\ndata: {payload}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
