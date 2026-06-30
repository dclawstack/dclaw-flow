"""Shared outbound HTTP for action nodes and connectors.

5xx is treated as a (likely transient) error and raised so the retry loop sees
it; 4xx flows through as output so a workflow can branch on it.
"""

from typing import Any

import httpx


async def http_request(
    url: str,
    method: str,
    headers: dict[str, Any],
    body: Any,
) -> dict[str, Any]:
    method = method.upper()
    if not url:
        return {"status": 0, "error": "Missing URL"}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(
                    url,
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, str) else None,
                )
            else:
                return {"status": 0, "error": f"Unsupported method: {method}"}
        except httpx.RequestError as e:
            raise RuntimeError(f"HTTP request failed: {e}") from e

    if response.status_code >= 500:
        raise RuntimeError(f"HTTP {response.status_code} from {url}")

    return {
        "status": response.status_code,
        "body": response.text,
        "headers": dict(response.headers),
    }


async def run_http_action(node_input: dict[str, Any]) -> dict[str, Any]:
    """Execute a plain HTTP action node from its resolved config."""
    return await http_request(
        url=node_input.get("url", ""),
        method=node_input.get("method", "GET"),
        headers=node_input.get("headers", {}),
        body=node_input.get("body"),
    )
