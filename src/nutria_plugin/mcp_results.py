"""MCP result normalization and declared-output conformance helpers.

These helpers intentionally do not import the MCP package. Plugin tests and
Nutria hosts can pass protocol values they already received while the SDK keeps
one definition of the payload against which manifest ``result_path`` bindings
are evaluated.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


class MCPResultContractError(ValueError):
    """Raised when a successful MCP result violates declared output bindings."""


def _decode_json_container(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
    return decoded if isinstance(decoded, dict | list) else value


def normalize_mcp_result(
    *,
    structured_content: Any = None,
    text_content: str | None = None,
) -> Any:
    """Return the canonical provider payload from an MCP tool response.

    Structured content is authoritative. FastMCP wraps tools annotated as
    returning ``str`` in an exact ``{"result": <string>}`` object; when that
    scalar is a complete JSON object or array, it represents the tool payload
    and is safely unwrapped. All other structured objects are preserved.
    """

    if structured_content is not None:
        if isinstance(structured_content, Mapping) and set(structured_content) == {"result"}:
            decoded = _decode_json_container(structured_content.get("result"))
            if isinstance(decoded, dict | list):
                return decoded
        return structured_content
    return _decode_json_container(text_content or "")


def project_result_path(payload: Any, result_path: str) -> Any:
    """Resolve one manifest result path or raise a conformance error."""

    declared_path = str(result_path or "").strip()
    if not declared_path:
        raise MCPResultContractError("declared output is missing result_path")
    if declared_path == "$":
        return payload
    if not declared_path.startswith("."):
        raise MCPResultContractError(f"invalid declared output path: {declared_path}")

    current = payload
    for part in declared_path[1:].split("."):
        if not part or not isinstance(current, Mapping) or part not in current:
            raise MCPResultContractError(
                f"declared output path did not materialize: {declared_path}"
            )
        current = current[part]
    if current is None:
        raise MCPResultContractError(
            f"declared output path did not materialize: {declared_path}"
        )
    return current


def validate_declared_outputs(
    payload: Any,
    produces: Iterable[Mapping[str, Any]],
) -> None:
    """Assert that every declared output exists with compatible cardinality."""

    for binding in produces:
        value = project_result_path(payload, str(binding.get("result_path") or ""))
        if binding.get("many") and not isinstance(value, list):
            raise MCPResultContractError(
                f"declared many output is not a list: {binding.get('result_path')}"
            )


def validate_capability_result(
    capability: Mapping[str, Any],
    *,
    structured_content: Any = None,
    text_content: str | None = None,
) -> Any:
    """Normalize an MCP result and validate one capability's output contract."""

    payload = normalize_mcp_result(
        structured_content=structured_content,
        text_content=text_content,
    )
    validate_declared_outputs(payload, capability.get("produces") or ())
    return payload
