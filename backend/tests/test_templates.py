"""Starter workflow templates: every template must be valid and instantiable."""

import pytest

from app.models import Workflow
from app.services.engine import validate_workflow
from app.templates import WORKFLOW_TEMPLATES


def test_templates_exist_with_unique_ids():
    assert len(WORKFLOW_TEMPLATES) >= 3
    ids = [t["id"] for t in WORKFLOW_TEMPLATES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("tpl", WORKFLOW_TEMPLATES, ids=lambda t: t["id"])
def test_each_template_passes_workflow_validation(tpl):
    wf = Workflow(nodes=tpl["nodes"], edges=tpl["edges"], trigger=tpl["trigger"])
    result = validate_workflow(wf)
    assert result.valid, f"{tpl['id']} invalid: {result.errors}"


@pytest.mark.asyncio
async def test_templates_endpoint_lists_templates(client):
    r = await client.get("/api/v1/flows/workflows/templates")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == len(WORKFLOW_TEMPLATES)
    expected = {"id", "name", "description", "category", "nodes", "edges", "trigger"}
    assert expected <= set(body[0])


@pytest.mark.asyncio
async def test_template_can_be_instantiated_as_workflow(client):
    tpl = (await client.get("/api/v1/flows/workflows/templates")).json()[0]
    created = await client.post(
        "/api/v1/flows/workflows",
        json={
            "name": tpl["name"],
            "description": tpl["description"],
            "nodes": tpl["nodes"],
            "edges": tpl["edges"],
            "trigger": tpl["trigger"],
        },
    )
    assert created.status_code == 201
    wid = created.json()["id"]
    validated = await client.post(f"/api/v1/flows/workflows/{wid}/validate")
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
