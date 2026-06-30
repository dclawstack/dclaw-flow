"""Owner-scoping helpers: fetch a resource only if it belongs to the user.

A non-owner gets the same 404 as a missing row so existence isn't leaked.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, User, Workflow


async def get_owned_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, user: User
) -> Workflow:
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


async def get_owned_execution(
    db: AsyncSession, execution_id: uuid.UUID, user: User
) -> Execution:
    execution = await db.get(Execution, execution_id)
    if execution is not None:
        workflow = await db.get(Workflow, execution.workflow_id)
        if workflow is not None and workflow.owner_id == user.id:
            return execution
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
    )
