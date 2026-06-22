"""Tests for the AI Flow Copilot (P0.1)."""

import pytest

from app.models import Workflow
from app.schemas import WorkflowCreate
from app.services import copilot

# --------------------------------------------------------------------------- #
# Heuristic generation (no LLM, no DB)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_falls_back_to_valid_heuristic(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    spec, source, model = await copilot.generate_workflow_spec(
        "When a webhook arrives, call an API and send a Slack message"
    )
    assert source == "heuristic"
    assert model is None
    assert isinstance(spec, WorkflowCreate)
    assert copilot.validate_spec(spec).valid


@pytest.mark.asyncio
async def test_generate_always_has_exactly_one_trigger(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    for desc in ["do something vague", "fetch and transform and notify", ""]:
        spec, _, _ = await copilot.generate_workflow_spec(desc or "x")
        triggers = [n for n in spec.nodes if n.type == "trigger"]
        assert len(triggers) == 1
        assert spec.nodes[0].type == "trigger"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "desc,expected",
    [
        ("trigger from a webhook then act", "webhook"),
        ("every day at 9am run this", "schedule"),
        ("just run it for me", "manual"),
    ],
)
async def test_trigger_type_detection(monkeypatch, desc, expected):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    spec, _, _ = await copilot.generate_workflow_spec(desc)
    assert spec.trigger.trigger_type == expected


@pytest.mark.asyncio
async def test_vague_description_still_produces_an_action(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    spec, _, _ = await copilot.generate_workflow_spec("hello there")
    assert any(n.type == "action" for n in spec.nodes)


# --------------------------------------------------------------------------- #
# Coercion of LLM-shaped JSON
# --------------------------------------------------------------------------- #


def test_coerce_spec_accepts_well_formed_llm_json():
    raw = {
        "name": "My Flow",
        "nodes": [
            {"id": "t", "type": "trigger", "label": "Start", "config": {}},
            {"id": "a", "type": "action", "label": "Do",
             "config": {"action_type": "http"}},
        ],
        "edges": [{"source": "t", "target": "a"}],
    }
    spec = copilot._coerce_spec(raw, "desc", None)
    assert spec is not None
    assert copilot.validate_spec(spec).valid
    assert spec.name == "My Flow"


def test_coerce_spec_injects_trigger_when_missing():
    raw = {"nodes": [{"id": "a", "type": "action", "config": {}}], "edges": []}
    spec = copilot._coerce_spec(raw, "desc", None)
    assert spec is not None
    assert spec.nodes[0].type == "trigger"
    assert copilot.validate_spec(spec).valid


def test_coerce_spec_demotes_extra_triggers():
    raw = {
        "nodes": [
            {"id": "t1", "type": "trigger", "config": {}},
            {"id": "t2", "type": "trigger", "config": {}},
        ],
        "edges": [{"source": "t1", "target": "t2"}],
    }
    spec = copilot._coerce_spec(raw, "desc", None)
    assert spec is not None
    assert len([n for n in spec.nodes if n.type == "trigger"]) == 1
    assert copilot.validate_spec(spec).valid


def test_coerce_spec_rejects_empty_nodes():
    assert copilot._coerce_spec({"nodes": []}, "desc", None) is None


# --------------------------------------------------------------------------- #
# Suggestions
# --------------------------------------------------------------------------- #


def test_suggest_recommends_trigger_first():
    wf = Workflow(nodes=[{"id": "a", "type": "action", "config": {}}], edges=[])
    suggestions = copilot.suggest_next_nodes(wf)
    assert suggestions[0].type == "trigger"


def test_suggest_caps_at_four():
    wf = Workflow(nodes=[], edges=[])
    assert len(copilot.suggest_next_nodes(wf)) <= 4


# --------------------------------------------------------------------------- #
# API endpoints
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_endpoint_without_persist(client, monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    resp = await client.post(
        "/api/v1/flows/copilot/generate",
        json={"description": "webhook then call an api", "persist": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["source"] == "heuristic"
    assert body["workflow"] is None
    assert len(body["spec"]["nodes"]) >= 2


@pytest.mark.asyncio
async def test_generate_endpoint_persists_workflow(client, monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    resp = await client.post(
        "/api/v1/flows/copilot/generate",
        json={"description": "send a slack message every day", "persist": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["workflow"] is not None
    wf_id = body["workflow"]["id"]

    got = await client.get(f"/api/v1/flows/workflows/{wf_id}")
    assert got.status_code == 200

    suggest = await client.post(f"/api/v1/flows/copilot/suggest/{wf_id}")
    assert suggest.status_code == 200
    assert "suggestions" in suggest.json()


# --------------------------------------------------------------------------- #
# Chat copilot
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_chat_build_intent_returns_spec(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    resp = await copilot.chat_reply(
        "Build a flow that calls an API when a webhook fires", [], []
    )
    assert resp.intent == "build"
    assert resp.suggested_workflow is not None
    assert copilot.validate_spec(resp.suggested_workflow).valid


@pytest.mark.asyncio
async def test_chat_question_is_grounded_in_workflows(monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    resp = await copilot.chat_reply(
        "how many workflows do I have?", [], ["Alpha", "Beta"]
    )
    assert resp.intent == "chat"
    assert resp.source == "heuristic"
    assert "2" in resp.reply and "Alpha" in resp.reply


@pytest.mark.asyncio
async def test_chat_endpoint(client, monkeypatch):
    monkeypatch.setattr(copilot.settings, "copilot_provider", "heuristic")
    resp = await client.post(
        "/api/v1/flows/copilot/chat",
        json={"message": "create a workflow that sends a slack alert", "history": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "build"
    assert body["suggested_workflow"] is not None
