"""Provider defaults are declared in the manifest; the preview rule has one shared definition."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import PREVIEW_CONFORMANCE_VECTORS, CapabilityDescriptor, check_prepared_preview
from tests.test_capability_contracts import _capability, _safety_contracts


def _with_input(name: str, *, required: bool) -> dict:
    return {
        "kind": "value",
        "semantic_field": name,
        "argument_name": name,
        "required": required,
        "data_class": "non_personal",
        "accepted_origins": ["current_user"],
    }


def _declared(**overrides) -> dict:
    base = _capability(**_safety_contracts())
    base["inputs"] = [*base["inputs"], _with_input("fecha", required=False)]
    return {**base, **overrides}


def test_provider_default_arguments_default_to_empty() -> None:
    assert CapabilityDescriptor.model_validate(_capability(**_safety_contracts())).provider_default_arguments == []


def test_optional_declared_input_may_be_a_provider_default() -> None:
    descriptor = CapabilityDescriptor.model_validate(_declared(provider_default_arguments=["fecha"]))

    assert descriptor.provider_default_arguments == ["fecha"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"provider_default_arguments": ["recipient"]}, "optional declared inputs"),
        ({"provider_default_arguments": ["unknown"]}, "optional declared inputs"),
        ({"provider_default_arguments": ["fecha", "fecha"]}, "must not repeat"),
        ({"provider_default_arguments": ["preview_only"]}, "control argument"),
        ({"provider_default_arguments": ["idempotency_key"]}, "control argument"),
    ],
)
def test_provider_default_arguments_are_validated(overrides: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        CapabilityDescriptor.model_validate(_declared(**overrides))


def test_provider_default_arguments_need_a_prepared_action() -> None:
    payload = _capability(
        exposure="host",
        non_callable_reason={"code": "host_only", "safe_summary": "Host executes it."},
        completion={"evidence": "none"},
        provider_default_arguments=["recipient"],
    )

    with pytest.raises(ValidationError, match="require a prepared_action"):
        CapabilityDescriptor.model_validate(payload)


@pytest.mark.parametrize("vector", PREVIEW_CONFORMANCE_VECTORS, ids=lambda item: item["name"])
def test_conformance_vectors_match_the_reference_rule(vector: dict) -> None:
    assert (
        check_prepared_preview(vector["capability"], vector["schema"], vector["requested"], vector["snapshot"])
        == vector["violations"]
    )


def test_personal_values_are_checked_for_presence_only() -> None:
    vector = next(item for item in PREVIEW_CONFORMANCE_VECTORS if item["name"] == "echoes_supplied_values")
    snapshot = {**vector["snapshot"], "recipient": "restored value"}

    assert check_prepared_preview(vector["capability"], vector["schema"], vector["requested"], snapshot) == [
        "supplied_argument_contradicted:recipient"
    ]
    assert (
        check_prepared_preview(
            vector["capability"], vector["schema"], vector["requested"], snapshot, personal_arguments={"recipient"}
        )
        == []
    )
