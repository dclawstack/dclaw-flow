"""Deterministic JSON-schema inference + payload validation for webhooks (P0.3).

No LLM: types are inferred structurally from an observed payload. (LLM-assisted
field descriptions are deferred to P1.) Validation is advisory — callers log
mismatches but do not reject ingestion.
"""

from typing import Any


def _json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "null"


def infer_schema(value: Any) -> dict[str, Any]:
    """Infer a minimal JSON-Schema-shaped description from one payload."""
    schema: dict[str, Any] = {"type": _json_type(value)}
    if isinstance(value, dict):
        schema["properties"] = {k: infer_schema(v) for k, v in value.items()}
        schema["required"] = sorted(value.keys())
    elif isinstance(value, list) and value:
        schema["items"] = infer_schema(value[0])
    return schema


def validate_payload(
    value: Any,
    schema: dict[str, Any],
    path: str = "",
) -> list[str]:
    """Return human-readable mismatches between a payload and an inferred schema."""
    errors: list[str] = []
    expected = schema.get("type")
    actual = _json_type(value)
    if expected and actual != expected:
        errors.append(f"{path or 'payload'}: expected {expected}, got {actual}")
        return errors

    if expected == "object":
        for key in schema.get("required", []):
            if not isinstance(value, dict) or key not in value:
                errors.append(f"missing field: {path}{key}")
        if isinstance(value, dict):
            for key, sub in schema.get("properties", {}).items():
                if key in value:
                    errors.extend(validate_payload(value[key], sub, f"{path}{key}."))
    return errors
