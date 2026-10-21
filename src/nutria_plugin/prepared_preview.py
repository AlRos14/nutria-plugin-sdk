"""Conformance rule for the exact preview a preparation capability returns.

A prepared action freezes the preview ``arguments`` and later re-executes exactly that invocation, so
the preview must be a valid, complete call of the tool that echoes what the caller supplied. This
module is the single definition of that rule for plugin tests and for hosts: it is pure (no I/O) and
reports violations as stable codes. ``PREVIEW_CONFORMANCE_VECTORS`` are shared cases both sides run
against their own implementation so the two cannot drift.

Host-only concerns (personal-data restoration, host-resolved targets, risk arguments) stay in the
host; ``personal_arguments`` only lets a host state which values are checked for presence.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

HOST_CONTROL_SCHEMA_KEY = "x-nutria-host-control"

UNDECLARED = "undeclared_argument"
MISSING_REQUIRED = "missing_required_argument"
OMITTED = "supplied_argument_omitted"
CONTRADICTED = "supplied_argument_contradicted"
NOT_A_PREVIEW = "snapshot_is_not_a_preview"


def _contains(prepared: Any, explicit: Any) -> bool:
    """Provider-added subfields are allowed; contradictory supplied data is not."""
    if isinstance(explicit, dict):
        return isinstance(prepared, dict) and all(
            key in prepared and _contains(prepared[key], value) for key, value in explicit.items()
        )
    if isinstance(explicit, list):
        return (
            isinstance(prepared, list)
            and len(prepared) == len(explicit)
            and all(_contains(p, e) for p, e in zip(prepared, explicit, strict=True))
        )
    return prepared == explicit


def _is_unset(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def check_prepared_preview(
    capability: Mapping[str, Any],
    input_schema: Mapping[str, Any],
    requested: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    *,
    personal_arguments: Collection[str] = (),
) -> list[str]:
    """Return ``"<code>:<argument>"`` violations; an empty list means the preview conforms."""
    properties = input_schema.get("properties") or {}
    prepared = capability.get("prepared_action") or {}
    idempotency = capability.get("idempotency") or {}
    preview_argument = str(prepared.get("preview_argument") or "")
    controls = {preview_argument, str(idempotency.get("argument_name") or "")} - {""}
    controls.update(
        name
        for name, descriptor in properties.items()
        if isinstance(descriptor, Mapping) and descriptor.get(HOST_CONTROL_SCHEMA_KEY)
    )
    provider_defaults = set(capability.get("provider_default_arguments") or ())
    violations: list[str] = []
    if preview_argument and snapshot.get(preview_argument) != prepared.get("preview_value"):
        violations.append(f"{NOT_A_PREVIEW}:{preview_argument}")
    violations += [f"{UNDECLARED}:{name}" for name in sorted(set(snapshot) - set(properties))]
    required = set(input_schema.get("required") or ()) - controls
    violations += [f"{MISSING_REQUIRED}:{name}" for name in sorted(required - set(snapshot))]
    personal = set(personal_arguments)
    for name, explicit in requested.items():
        if name in controls:
            continue
        if name in provider_defaults and _is_unset(explicit):
            continue
        if name not in snapshot:
            violations.append(f"{OMITTED}:{name}")
        elif name not in personal and not _contains(snapshot[name], explicit):
            violations.append(f"{CONTRADICTED}:{name}")
    return violations


_CAPABILITY = {
    "prepared_action": {"preview_argument": "preview_only", "preview_value": True},
    "idempotency": {"argument_name": "idempotency_key"},
    "provider_default_arguments": ["fecha"],
}
_SCHEMA = {
    "properties": {
        "recipient": {"type": "string"},
        "fecha": {"type": "string"},
        "note": {"type": "string"},
        "preview_only": {"type": "boolean"},
        "idempotency_key": {"type": "string"},
    },
    "required": ["recipient"],
}

#: Shared cases: ``violations`` is the exact expected result of ``check_prepared_preview``.
PREVIEW_CONFORMANCE_VECTORS: tuple[dict[str, Any], ...] = (
    {
        "name": "echoes_supplied_values",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "preview_only": True},
        "snapshot": {"recipient": "Ana", "preview_only": True},
        "violations": [],
    },
    {
        "name": "provider_default_fills_an_empty_argument",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "fecha": "", "preview_only": True},
        "snapshot": {"recipient": "Ana", "fecha": "21/10/2026", "preview_only": True},
        "violations": [],
    },
    {
        "name": "provider_default_never_overrides_a_supplied_value",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "fecha": "22/10/2026", "preview_only": True},
        "snapshot": {"recipient": "Ana", "fecha": "21/10/2026", "preview_only": True},
        "violations": ["supplied_argument_contradicted:fecha"],
    },
    {
        "name": "undeclared_default_stays_strict_when_empty",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "note": "", "preview_only": True},
        "snapshot": {"recipient": "Ana", "note": "x", "preview_only": True},
        "violations": ["supplied_argument_contradicted:note"],
    },
    {
        "name": "supplied_empty_argument_must_not_vanish",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "note": "", "preview_only": True},
        "snapshot": {"recipient": "Ana", "preview_only": True},
        "violations": ["supplied_argument_omitted:note"],
    },
    {
        "name": "api_parameter_names_are_not_tool_arguments",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "preview_only": True},
        "snapshot": {"idRecipient": "Ana", "preview_only": True},
        "violations": [
            "undeclared_argument:idRecipient",
            "missing_required_argument:recipient",
            "supplied_argument_omitted:recipient",
        ],
    },
    {
        "name": "snapshot_must_be_a_preview",
        "capability": _CAPABILITY,
        "schema": _SCHEMA,
        "requested": {"recipient": "Ana", "preview_only": True},
        "snapshot": {"recipient": "Ana", "preview_only": False},
        "violations": ["snapshot_is_not_a_preview:preview_only"],
    },
)
