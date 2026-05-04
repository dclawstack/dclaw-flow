"""Seed sample data for development."""

import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Workflow


async def seed_data() -> None:
    """Create a sample workflow if none exists."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Workflow).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return

        sample_workflow = Workflow(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="Hello World Flow",
            description="A simple sample workflow with 3 nodes",
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            status="active",
            nodes=[
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 150},
                    "config": {"trigger_type": "manual"},
                    "label": "Manual Trigger",
                    "timeout_seconds": 30,
                },
                {
                    "id": "action-1",
                    "type": "action",
                    "position": {"x": 350, "y": 150},
                    "config": {
                        "action_type": "http",
                        "url": "https://httpbin.org/get",
                        "method": "GET",
                    },
                    "label": "HTTP Request",
                    "timeout_seconds": 30,
                },
                {
                    "id": "transform-1",
                    "type": "transform",
                    "position": {"x": 600, "y": 150},
                    "config": {"mapping": {"result": "$body"}},
                    "label": "Transform Response",
                    "timeout_seconds": 30,
                },
            ],
            edges=[
                {"id": "e1", "source": "trigger-1", "target": "action-1"},
                {"id": "e2", "source": "action-1", "target": "transform-1"},
            ],
            trigger={"trigger_type": "manual", "config": {}},
        )
        db.add(sample_workflow)
        await db.commit()
