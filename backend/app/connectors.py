"""Token-based connectors: run a node against a stored, decrypted credential.

A connection stores an encrypted secret blob (the auth fields); a node supplies
the per-call fields. `run_connector` receives the already-decrypted secret —
it never touches the database or the ciphertext.
"""

from typing import Any

from app.services.http_action import http_request

# Catalog surfaced to the UI: what secret fields a connection needs, and what
# fields a node supplies per call. Kept deliberately small (token-auth only).
CONNECTORS: dict[str, dict[str, Any]] = {
    "authenticated_http": {
        "label": "Authenticated HTTP",
        "secret_fields": ["auth_type", "token", "header_name"],
        "node_fields": ["url", "method", "body"],
    },
    "slack_webhook": {
        "label": "Slack (Incoming Webhook)",
        "secret_fields": ["webhook_url"],
        "node_fields": ["text"],
    },
}


async def run_connector(
    connector_type: str,
    secret: dict[str, Any],
    node_input: dict[str, Any],
) -> dict[str, Any]:
    if connector_type == "authenticated_http":
        return await _run_authenticated_http(secret, node_input)
    if connector_type == "slack_webhook":
        return await _run_slack_webhook(secret, node_input)
    raise RuntimeError(f"Unknown connector type: {connector_type}")


async def _run_authenticated_http(
    secret: dict[str, Any], node_input: dict[str, Any]
) -> dict[str, Any]:
    headers = dict(node_input.get("headers", {}))
    token = secret.get("token", "")
    if secret.get("auth_type") == "api_key":
        headers[secret.get("header_name") or "X-API-Key"] = token
    else:  # default: bearer
        headers["Authorization"] = f"Bearer {token}"
    return await http_request(
        url=node_input.get("url", ""),
        method=node_input.get("method", "GET"),
        headers=headers,
        body=node_input.get("body"),
    )


async def _run_slack_webhook(
    secret: dict[str, Any], node_input: dict[str, Any]
) -> dict[str, Any]:
    return await http_request(
        url=secret.get("webhook_url", ""),
        method="POST",
        headers={},
        body={"text": node_input.get("text", "")},
    )
