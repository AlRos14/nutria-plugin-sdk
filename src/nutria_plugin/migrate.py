"""Mechanical manifest migration 5.0 -> 6.0 with an explicit human-review report.

Only changes that are structurally determined are applied. Everything that encodes a
judgement (where an effect lands, what evidence completes it, how sensitive a field is)
is given a *conservative* value and listed in the returned review items. The migrated
manifest is never trusted blindly: run ``nutria-plugin validate`` and review each item.
"""

from __future__ import annotations

import copy
from typing import Any

_COMPLETION_BASIS_DEFAULT = "provider_outcome"


def migrate_manifest_5_to_6(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if manifest.get("schema_version") != "5.0":
        raise ValueError("only schema_version 5.0 manifests can be migrated")
    migrated = copy.deepcopy(manifest)
    migrated["schema_version"] = "6.0"
    review: list[str] = []
    for capability in migrated.get("capabilities", []):
        cid = capability.get("id", "?")
        effect = capability.get("effect")
        if "effect_scope" not in capability:
            if effect in {"read", "external_write"}:
                capability["effect_scope"] = "world"
                if effect == "read":
                    review.append(f"{cid}: effect_scope set to 'world' (confirm; read)")
            else:
                capability["effect_scope"] = "world" if capability.get("connection_id") else "internal_state"
                review.append(
                    f"{cid}: effect_scope guessed as {capability['effect_scope']!r} for a write"
                )
        completion = capability.get("completion")
        if effect == "read":
            capability.pop("completion", None)
        elif completion is None:
            capability["completion"] = {"evidence": "none"}
            review.append(f"{cid}: non-read capability had no completion; set evidence 'none'")
        elif "evidence" not in completion:
            capability["completion"] = {
                "evidence": "declared",
                "receipts": completion.get("receipts", []),
                "basis": _COMPLETION_BASIS_DEFAULT,
                "targets": "single",
            }
            review.append(
                f"{cid}: completion basis defaulted to {_COMPLETION_BASIS_DEFAULT!r}; "
                "choose the real basis and targets"
            )
        for binding in capability.get("inputs", []):
            sensitivity = binding.pop("sensitivity", None)
            if "data_class" not in binding:
                if sensitivity == "personal":
                    binding["data_class"] = "personal_identifier"
                    review.append(
                        f"{cid}.{binding.get('semantic_field')}: personal -> personal_identifier "
                        "(use personal_content or special_category if applicable)"
                    )
                else:
                    binding["data_class"] = "non_personal"
                    review.append(
                        f"{cid}.{binding.get('semantic_field')}: safe -> non_personal "
                        "(use business_resource_identifier / operational_identifier if it is one)"
                    )
        for output in capability.get("produces", []):
            if "data_class" not in output:
                output["data_class"] = "non_personal"
                review.append(f"{cid}.{output.get('output_name')}: output data_class defaulted")
    return migrated, review
