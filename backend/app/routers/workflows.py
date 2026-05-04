"""Workflow CRUD router."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Execution, Workflow
from app.schemas import (
    ValidationResponse,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.engine import validate_workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
) -> Workflow:
    workflow = Workflow(
        name=data.name,
        description=data.description,
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
) -> dict[str, Any]:
    result = await db.execute(select(Workflow).offset(skip).limit(limit))
    workflows = result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(Workflow))
    total = total_result.scalar() or 0
    return {"items": workflows, "total": total}


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Workflow:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
) -> Workflow:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "nodes" in update_data and update_data["nodes"] is not None:
        update_data["nodes"] = [node.model_dump() for node in update_data["nodes"]]
    if "edges" in update_data and update_data["edges"] is not None:
        update_data["edges"] = [edge.model_dump() for edge in update_data["edges"]]
    if "trigger" in update_data and update_data["trigger"] is not None:
        update_data["trigger"] = update_data["trigger"].model_dump()

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
) -> None:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    await db.delete(workflow)
    await db.commit()


@router.post("/{workflow_id}/validate", response_model=ValidationResponse)
async def validate_workflow_endpoint(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ValidationResponse:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return validate_workflow(workflow)


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
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
