"""Pydantic v2 schemas for API requests and responses."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NodeSchema(BaseModel):
    id: str
    type: Literal["trigger", "action", "conditional", "loop", "delay", "merge", "transform"]
    position: dict[str, float]
    config: dict[str, Any]
    label: str | None = None
    timeout_seconds: int = 30


class EdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    condition: str | None = None
    label: str | None = None


class TriggerConfig(BaseModel):
    trigger_type: Literal["manual", "webhook", "schedule"] = "manual"
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    nodes: list[NodeSchema] = Field(default_factory=list)
    edges: list[EdgeSchema] = Field(default_factory=list)
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[NodeSchema] | None = None
    edges: list[EdgeSchema] | None = None
    trigger: TriggerConfig | None = None
    status: Literal["draft", "active", "paused", "archived"] | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    status: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    trigger: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[str]


class NodeExecutionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: str
    status: str
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error: dict[str, Any] | None
    created_at: datetime


class ExecutionCreate(BaseModel):
    payload: dict[str, Any] | None = None
    wait_for_completion: bool = False


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    trigger_source: str
    trigger_payload: dict[str, Any] | None
    started_at: datetime
    completed_at: datetime | None
    error: dict[str, Any] | None
    node_executions: list[NodeExecutionSchema] = []


class ExecutionListResponse(BaseModel):
    items: list[ExecutionResponse]
    total: int


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


class WebhookPayload(BaseModel):
    data: dict[str, Any] | None = None
