"""AI Flow Copilot (P0.1) — generate workflows from natural language.

Generation order (provider="auto"): local Ollama → cloud OpenRouter →
deterministic heuristic. The heuristic is always available, so the copilot
produces a valid workflow even with no LLM configured (offline / CI).
"""

import json
import re
from typing import Any

import httpx

from app.config import settings
from app.models import Workflow
from app.schemas import (
    CopilotChatMessage,
    CopilotChatResponse,
    EdgeSchema,
    NodeSchema,
    NodeSuggestion,
    TriggerConfig,
    ValidationResponse,
    WorkflowCreate,
)
from app.services.engine import validate_workflow

ALLOWED_TYPES = {
    "trigger", "action", "conditional", "loop", "delay", "merge", "transform",
}
MAX_NODES = 60
_X_STEP = 220
_Y = 150

_SYSTEM_PROMPT = (
    "You are a workflow automation expert. Convert the user's request into a JSON "
    "workflow. Respond with ONLY a JSON object, no prose. Schema:\n"
    '{"name": str, "description": str, '
    '"nodes": [{"id": str, "type": one of '
    '["trigger","action","conditional","loop","delay","merge","transform"], '
    '"label": str, "config": object}], '
    '"edges": [{"source": node_id, "target": node_id}]}\n'
    "Rules: exactly ONE node has type 'trigger' and it is the entry point; nodes form "
    "a connected directed acyclic graph; action nodes use config "
    '{"action_type":"http","url":...,"method":...}; delay nodes use '
    '{"duration_seconds":int}; conditional nodes use {"expression":str}.'
)

_CHAT_SYSTEM_PROMPT = (
    "You are the DClaw Flow Copilot, an assistant for a visual workflow "
    "automation platform (like Zapier/n8n). Help users understand and build "
    "automations. Be concise (2-4 sentences). Suggest a concrete next action. "
    "When a user wants to build something, tell them to describe the automation "
    "and you will generate it."
)

_BUILD_KEYWORDS = (
    "build", "create", "make", "generate", "automate", "set up", "setup",
    "add a flow", "new flow", "new workflow", "when ", "every time",
)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


async def generate_workflow_spec(
    description: str,
    name: str | None = None,
) -> tuple[WorkflowCreate, str, str | None]:
    """Return (spec, source, model). Falls back to a heuristic on any failure."""
    provider = settings.copilot_provider
    order = _provider_order(provider)

    for source in order:
        raw, model = await _try_provider(source, description)
        if raw is None:
            continue
        spec = _coerce_spec(raw, description, name)
        if spec is not None and validate_spec(spec).valid:
            return spec, source, model

    return _heuristic_spec(description, name), "heuristic", None


def validate_spec(spec: WorkflowCreate) -> ValidationResponse:
    """Validate a generated spec using the same engine as saved workflows."""
    transient = Workflow(
        nodes=[n.model_dump() for n in spec.nodes],
        edges=[e.model_dump() for e in spec.edges],
    )
    return validate_workflow(transient)


def suggest_next_nodes(workflow: Workflow) -> list[NodeSuggestion]:
    """Suggest sensible next nodes for an in-progress workflow."""
    nodes = workflow.nodes or []
    types = {n.get("type") for n in nodes}
    suggestions: list[NodeSuggestion] = []

    if "trigger" not in types:
        suggestions.append(
            NodeSuggestion(
                type="trigger",
                label="Add a trigger",
                reason="Every workflow needs exactly one entry point.",
            )
        )
    if "action" not in types:
        suggestions.append(
            NodeSuggestion(
                type="action",
                label="Call an HTTP endpoint",
                reason="Most flows act on an external service after the trigger.",
            )
        )
    if "conditional" not in types and len(nodes) >= 2:
        suggestions.append(
            NodeSuggestion(
                type="conditional",
                label="Branch on a condition",
                reason="Route the flow based on a previous step's output.",
            )
        )
    if "transform" not in types and "action" in types:
        suggestions.append(
            NodeSuggestion(
                type="transform",
                label="Reshape the data",
                reason="Map upstream output into the shape the next step needs.",
            )
        )
    return suggestions[:4]


async def chat_reply(
    message: str,
    history: list[CopilotChatMessage],
    workflow_names: list[str],
) -> CopilotChatResponse:
    """Answer a copilot chat turn; build a workflow when that's the intent."""
    if _detect_intent(message) == "build":
        spec, source, model = await generate_workflow_spec(message)
        return CopilotChatResponse(
            reply=_summarize_spec(spec),
            intent="build",
            source=source,
            model=model,
            suggested_workflow=spec,
        )

    for source in _provider_order(settings.copilot_provider):
        reply, model = await _try_chat_provider(
            source, message, history, workflow_names
        )
        if reply:
            return CopilotChatResponse(
                reply=reply, intent="chat", source=source, model=model
            )

    return CopilotChatResponse(
        reply=_heuristic_chat(message, workflow_names),
        intent="chat",
        source="heuristic",
        model=None,
    )


# --------------------------------------------------------------------------- #
# Provider calls
# --------------------------------------------------------------------------- #


def _provider_order(provider: str) -> list[str]:
    if provider == "ollama":
        return ["ollama"]
    if provider == "openrouter":
        return ["openrouter"]
    if provider == "heuristic":
        return []
    # auto: local first, then cloud
    order = ["ollama"]
    if settings.openrouter_api_key:
        order.append("openrouter")
    return order


async def _try_provider(
    source: str,
    description: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call a provider; return (parsed_json, model) or (None, model) on failure."""
    try:
        if source == "ollama":
            return await _call_ollama(description), settings.ollama_model
        if source == "openrouter":
            return await _call_openrouter(description), settings.openrouter_model
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError):
        return None, None
    return None, None


async def _call_ollama(description: str) -> dict[str, Any] | None:
    payload = {
        "model": settings.ollama_model,
        "prompt": f"{_SYSTEM_PROMPT}\n\nRequest: {description}",
        "format": "json",
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=settings.copilot_timeout_seconds) as client:
        resp = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
        resp.raise_for_status()
        return _extract_json(resp.json().get("response", ""))


async def _call_openrouter(description: str) -> dict[str, Any] | None:
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
    async with httpx.AsyncClient(timeout=settings.copilot_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.openrouter_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of a model response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group(0)) if match else None


async def _try_chat_provider(
    source: str,
    message: str,
    history: list[CopilotChatMessage],
    workflow_names: list[str],
) -> tuple[str | None, str | None]:
    """Free-text chat completion; return (reply, model) or (None, model)."""
    messages = _build_chat_messages(message, history, workflow_names)
    try:
        if source == "ollama":
            return await _chat_ollama(messages), settings.ollama_model
        if source == "openrouter":
            return await _chat_openrouter(messages), settings.openrouter_model
    except (httpx.HTTPError, KeyError, ValueError):
        return None, None
    return None, None


def _build_chat_messages(
    message: str,
    history: list[CopilotChatMessage],
    workflow_names: list[str],
) -> list[dict[str, str]]:
    context = (
        f" The user currently has {len(workflow_names)} workflow(s): "
        f"{', '.join(workflow_names[:10])}."
        if workflow_names
        else " The user has no workflows yet."
    )
    messages = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT + context}]
    messages += [{"role": m.role, "content": m.content} for m in history[-6:]]
    messages.append({"role": "user", "content": message})
    return messages


async def _chat_ollama(messages: list[dict[str, str]]) -> str | None:
    payload = {"model": settings.ollama_model, "messages": messages, "stream": False}
    async with httpx.AsyncClient(timeout=settings.copilot_timeout_seconds) as client:
        resp = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        return (resp.json().get("message") or {}).get("content") or None


async def _chat_openrouter(messages: list[dict[str, str]]) -> str | None:
    payload = {"model": settings.openrouter_model, "messages": messages}
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
    async with httpx.AsyncClient(timeout=settings.copilot_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.openrouter_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or None


# --------------------------------------------------------------------------- #
# Coercion of LLM output into a valid spec
# --------------------------------------------------------------------------- #


def _coerce_spec(
    raw: dict[str, Any],
    description: str,
    name: str | None,
) -> WorkflowCreate | None:
    """Best-effort coercion of model JSON into a valid WorkflowCreate."""
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        return None

    nodes: list[NodeSchema] = []
    for i, item in enumerate(raw_nodes[:MAX_NODES]):
        if not isinstance(item, dict):
            continue
        node_type = item.get("type") if item.get("type") in ALLOWED_TYPES else "action"
        config = item.get("config")
        nodes.append(
            NodeSchema(
                id=str(item.get("id") or f"{node_type}-{i}"),
                type=node_type,
                position={"x": float(100 + i * _X_STEP), "y": float(_Y)},
                config=config if isinstance(config, dict) else {},
                label=item.get("label") or node_type.title(),
            )
        )
    if not nodes:
        return None

    nodes = _ensure_single_trigger(nodes)
    edges = _coerce_edges(raw.get("edges"), nodes)

    return WorkflowCreate(
        name=name or str(raw.get("name") or _derive_name(description)),
        description=str(raw.get("description") or description),
        nodes=nodes,
        edges=edges,
        trigger=_trigger_for(nodes[0]),
    )


def _ensure_single_trigger(nodes: list[NodeSchema]) -> list[NodeSchema]:
    """Guarantee exactly one trigger node, as the first node."""
    triggers = [n for n in nodes if n.type == "trigger"]
    if len(triggers) == 1 and nodes[0].type == "trigger":
        return nodes
    # Demote extra triggers to actions.
    seen = False
    for n in nodes:
        if n.type == "trigger":
            if seen:
                n.type = "action"
            seen = True
    if not seen:
        nodes.insert(
            0,
            NodeSchema(
                id="trigger-0",
                type="trigger",
                position={"x": 100.0, "y": float(_Y)},
                config={"trigger_type": "manual"},
                label="Manual Trigger",
            ),
        )
    # Move the trigger to the front.
    nodes.sort(key=lambda n: 0 if n.type == "trigger" else 1)
    return nodes


def _coerce_edges(raw_edges: Any, nodes: list[NodeSchema]) -> list[EdgeSchema]:
    """Keep valid edges; otherwise build a linear chain through the nodes."""
    ids = {n.id for n in nodes}
    edges: list[EdgeSchema] = []
    if isinstance(raw_edges, list):
        for i, e in enumerate(raw_edges):
            if not isinstance(e, dict):
                continue
            src, tgt = e.get("source"), e.get("target")
            if src in ids and tgt in ids and src != tgt:
                eid = str(e.get("id") or f"edge-{i}")
                edges.append(EdgeSchema(id=eid, source=src, target=tgt))
    transient = Workflow(
        nodes=[n.model_dump() for n in nodes],
        edges=[e.model_dump() for e in edges],
    )
    if edges and validate_workflow(transient).valid:
        return edges
    return _linear_edges(nodes)


# --------------------------------------------------------------------------- #
# Deterministic heuristic generator
# --------------------------------------------------------------------------- #

_KEYWORD_NODES: list[tuple[tuple[str, ...], str, str, dict[str, Any]]] = [
    (("if", "when", "condition", "check", "only"), "conditional", "Check condition",
     {"expression": "true"}),
    (("transform", "map", "format", "convert", "parse", "reshape"), "transform",
     "Transform data", {"mapping": {}}),
    (("wait", "delay", "pause", "sleep", "after"), "delay", "Wait",
     {"duration_seconds": 5}),
    (("http", "api", "request", "fetch", "call", "post", "get ", "webhook out"),
     "action", "HTTP Request",
     {"action_type": "http", "url": "https://httpbin.org/get", "method": "GET"}),
    (("slack", "email", "notify", "send", "message", "alert", "notification"), "action",
     "Send Notification",
     {"action_type": "http", "url": "https://httpbin.org/post", "method": "POST"}),
]


def _heuristic_spec(description: str, name: str | None) -> WorkflowCreate:
    """Build a valid linear workflow by keyword-matching the description."""
    text = description.lower()
    trigger = _detect_trigger(text)
    nodes: list[NodeSchema] = [trigger]

    for keywords, node_type, label, config in _KEYWORD_NODES:
        if any(k in text for k in keywords):
            idx = len(nodes)
            nodes.append(
                NodeSchema(
                    id=f"{node_type}-{idx}",
                    type=node_type,
                    position={"x": float(100 + idx * _X_STEP), "y": float(_Y)},
                    config=config,
                    label=label,
                )
            )

    if len(nodes) == 1:  # nothing matched — add a default action so the flow acts
        nodes.append(
            NodeSchema(
                id="action-1",
                type="action",
                position={"x": float(100 + _X_STEP), "y": float(_Y)},
                config={
                    "action_type": "http",
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                },
                label="HTTP Request",
            )
        )

    return WorkflowCreate(
        name=name or _derive_name(description),
        description=description,
        nodes=nodes,
        edges=_linear_edges(nodes),
        trigger=_trigger_for(trigger),
    )


def _detect_trigger(text: str) -> NodeSchema:
    schedule_words = ("schedule", "every", "daily", "hourly", "cron", "weekly")
    if "webhook" in text:
        ttype, label = "webhook", "Webhook Trigger"
    elif any(k in text for k in schedule_words):
        ttype, label = "schedule", "Schedule Trigger"
    else:
        ttype, label = "manual", "Manual Trigger"
    return NodeSchema(
        id="trigger-0",
        type="trigger",
        position={"x": 100.0, "y": float(_Y)},
        config={"trigger_type": ttype},
        label=label,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _linear_edges(nodes: list[NodeSchema]) -> list[EdgeSchema]:
    return [
        EdgeSchema(id=f"edge-{i}", source=nodes[i].id, target=nodes[i + 1].id)
        for i in range(len(nodes) - 1)
    ]


def _trigger_for(trigger_node: NodeSchema) -> TriggerConfig:
    ttype = trigger_node.config.get("trigger_type", "manual")
    if ttype not in ("manual", "webhook", "schedule"):
        ttype = "manual"
    return TriggerConfig(trigger_type=ttype, config={})


def _derive_name(description: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", description)[:6]
    return " ".join(w.capitalize() for w in words) or "Generated Flow"


def _detect_intent(message: str) -> str:
    text = message.lower()
    return "build" if any(k in text for k in _BUILD_KEYWORDS) else "chat"


def _summarize_spec(spec: WorkflowCreate) -> str:
    steps = " → ".join(n.label or n.type for n in spec.nodes)
    return (
        f"I drafted \"{spec.name}\" with {len(spec.nodes)} steps: {steps}. "
        "Review it on the canvas, then create it if it looks right."
    )


def _heuristic_chat(message: str, workflow_names: list[str]) -> str:
    text = message.lower()
    if any(k in text for k in ("how many", "list", "my workflow", "my flow")):
        if not workflow_names:
            return "You don't have any workflows yet. Describe one and I'll build it."
        names = ", ".join(workflow_names[:10])
        return f"You have {len(workflow_names)} workflow(s): {names}."
    return (
        "I'm the Flow Copilot. Describe an automation and I'll build it — "
        "for example: 'When a webhook fires, call an API and post to Slack.'"
    )
