"""AI Flow Copilot router (P0.1)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Workflow
from app.schemas import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotGenerateRequest,
    CopilotGenerateResponse,
    CopilotSuggestResponse,
)
from app.services.copilot import (
    chat_reply,
    generate_workflow_spec,
    suggest_next_nodes,
    validate_spec,
)

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/generate", response_model=CopilotGenerateResponse)
async def generate(
    data: CopilotGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> CopilotGenerateResponse:
    """Generate a workflow from a natural-language description."""
    spec, source, model = await generate_workflow_spec(data.description, data.name)
    validation = validate_spec(spec)

    workflow = None
    if data.persist and validation.valid:
        workflow = Workflow(
            name=spec.name,
            description=spec.description,
            nodes=[node.model_dump() for node in spec.nodes],
            edges=[edge.model_dump() for edge in spec.edges],
            trigger=spec.trigger.model_dump(),
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

    return CopilotGenerateResponse(
        source=source,
        model=model,
        valid=validation.valid,
        errors=validation.errors,
        spec=spec,
        workflow=workflow,
    )


@router.post("/suggest/{workflow_id}", response_model=CopilotSuggestResponse)
async def suggest(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CopilotSuggestResponse:
    """Suggest sensible next nodes for an existing workflow."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return CopilotSuggestResponse(suggestions=suggest_next_nodes(workflow))


@router.post("/chat", response_model=CopilotChatResponse)
async def chat(
    data: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
) -> CopilotChatResponse:
    """Floating-copilot chat turn, grounded in the user's existing workflows."""
    result = await db.execute(select(Workflow.name).limit(50))
    workflow_names = [name for (name,) in result.all()]
    return await chat_reply(data.message, data.history, workflow_names)
