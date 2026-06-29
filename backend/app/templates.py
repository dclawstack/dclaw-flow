"""Curated starter workflow templates for onboarding.

Each template is a ready-to-instantiate workflow body (the same shape the create
API accepts). They are intentionally static data — no DB table — and every one
is asserted valid by tests/test_templates.py so the gallery can never offer a
broken starting point.
"""

from typing import Any


def _node(
    node_id: str,
    node_type: str,
    x: int,
    label: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "position": {"x": x, "y": 150},
        "config": config,
        "label": label,
        "timeout_seconds": 30,
    }


WORKFLOW_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "webhook-to-notification",
        "name": "Webhook → Notification",
        "description": "When a webhook arrives, POST a message to Slack or any "
        "incoming-webhook URL.",
        "category": "Notifications",
        "nodes": [
            _node("trigger-0", "trigger", 80, "Webhook", {"trigger_type": "webhook"}),
            _node(
                "action-1",
                "action",
                340,
                "Send Notification",
                {
                    "action_type": "http",
                    "url": "https://hooks.slack.com/services/REPLACE/ME",
                    "method": "POST",
                },
            ),
        ],
        "edges": [{"id": "e0", "source": "trigger-0", "target": "action-1"}],
        "trigger": {"trigger_type": "webhook", "config": {}},
    },
    {
        "id": "scheduled-health-check",
        "name": "Scheduled Health Check",
        "description": "On a schedule, call an endpoint and branch on whether it "
        "is healthy.",
        "category": "Monitoring",
        "nodes": [
            _node(
                "trigger-0", "trigger", 80, "Schedule", {"trigger_type": "schedule"}
            ),
            _node(
                "action-1",
                "action",
                340,
                "Check Endpoint",
                {
                    "action_type": "http",
                    "url": "https://httpbin.org/status/200",
                    "method": "GET",
                },
            ),
            _node(
                "conditional-2",
                "conditional",
                600,
                "Healthy?",
                {"expression": "$body"},
            ),
        ],
        "edges": [
            {"id": "e0", "source": "trigger-0", "target": "action-1"},
            {"id": "e1", "source": "action-1", "target": "conditional-2"},
        ],
        "trigger": {"trigger_type": "schedule", "config": {"cron": "0 * * * *"}},
    },
    {
        "id": "fetch-and-transform",
        "name": "Fetch & Transform",
        "description": "Manually fetch JSON from an API and reshape it with a "
        "field mapping.",
        "category": "Data",
        "nodes": [
            _node("trigger-0", "trigger", 80, "Manual", {"trigger_type": "manual"}),
            _node(
                "action-1",
                "action",
                340,
                "HTTP Request",
                {
                    "action_type": "http",
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                },
            ),
            _node(
                "transform-2",
                "transform",
                600,
                "Reshape",
                {"mapping": {"result": "$body"}},
            ),
        ],
        "edges": [
            {"id": "e0", "source": "trigger-0", "target": "action-1"},
            {"id": "e1", "source": "action-1", "target": "transform-2"},
        ],
        "trigger": {"trigger_type": "manual", "config": {}},
    },
    {
        "id": "webhook-delay-notify",
        "name": "Delayed Notification",
        "description": "On a webhook, wait a few seconds, then send a notification "
        "— handy for debounced alerts.",
        "category": "Notifications",
        "nodes": [
            _node("trigger-0", "trigger", 80, "Webhook", {"trigger_type": "webhook"}),
            _node("delay-1", "delay", 340, "Wait", {"duration_seconds": 5}),
            _node(
                "action-2",
                "action",
                600,
                "Send Notification",
                {
                    "action_type": "http",
                    "url": "https://hooks.slack.com/services/REPLACE/ME",
                    "method": "POST",
                },
            ),
        ],
        "edges": [
            {"id": "e0", "source": "trigger-0", "target": "delay-1"},
            {"id": "e1", "source": "delay-1", "target": "action-2"},
        ],
        "trigger": {"trigger_type": "webhook", "config": {}},
    },
]


def list_templates() -> list[dict[str, Any]]:
    return WORKFLOW_TEMPLATES
