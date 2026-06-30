"""Workflow CRUD router."""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Execution, User, Workflow
from app.ownership import get_owned_workflow
from app.schemas import (
    ExecutionCreate,
    ExecutionResponse,
    ValidationResponse,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowTemplate,
    WorkflowUpdate,
)
from app.services.engine import validate_workflow
from app.services.queue import run_execution_durable
from app.templates import list_templates

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    workflow = Workflow(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
        nodes=[node.model_dump() for node in data.nodes],
        edges=[edge.model_dump() for edge in data.edges],
        trigger=data.trigger.model_dump(),
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    owned = Workflow.owner_id == current_user.id
    result = await db.execute(
        select(Workflow).where(owned).offset(skip).limit(limit)
    )
    workflows = result.scalars().all()
    total_result = await db.execute(
        select(func.count()).select_from(Workflow).where(owned)
    )
    total = total_result.scalar() or 0
    return {"items": workflows, "total": total}


@router.get("/templates", response_model=list[WorkflowTemplate])
async def get_templates() -> list[dict[str, Any]]:
    """Curated starter templates (static; defined before /{workflow_id})."""
    return list_templates()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    return await get_owned_workflow(db, workflow_id, current_user)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    workflow = await get_owned_workflow(db, workflow_id, current_user)

    # model_dump already recurses into NodeSchema/EdgeSchema/TriggerConfig, so
    # nodes/edges/trigger arrive as plain dicts ready for the JSON columns.
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(workflow, key, value)

    workflow.version += 1
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    workflow = await get_owned_workflow(db, workflow_id, current_user)
    await db.delete(workflow)
    await db.commit()


@router.post("/{workflow_id}/validate", response_model=ValidationResponse)
async def validate_workflow_endpoint(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationResponse:
    workflow = await get_owned_workflow(db, workflow_id, current_user)
    return validate_workflow(workflow)


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    await get_owned_workflow(db, workflow_id, current_user)
    result = await db.execute(
        select(Execution)
        .where(Execution.workflow_id == workflow_id)
        .order_by(Execution.started_at.desc())
        .offset(skip)
        .limit(limit),
    )
    executions = result.scalars().all()
    total_result = await db.execute(
        select(func.count())
        .select_from(Execution)
        .where(Execution.workflow_id == workflow_id),
    )
    total = total_result.scalar() or 0
    return {"items": executions, "total": total}


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow_endpoint(
    workflow_id: uuid.UUID,
    data: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Execution:
    # Ownership check (raises 404 if not the caller's workflow).
    await get_owned_workflow(db, workflow_id, current_user)

    execution = Execution(
        workflow_id=workflow_id,
        status="pending",
        trigger_source="manual",
        trigger_payload=data.payload,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Both paths claim the job (so the queue worker won't double-run it); the
    # sync path awaits it, the async path lets the worker/task drive it.
    if data.wait_for_completion:
        await run_execution_durable(execution.id)
        await db.refresh(execution)
    else:
        asyncio.create_task(run_execution_durable(execution.id))

    return execution
