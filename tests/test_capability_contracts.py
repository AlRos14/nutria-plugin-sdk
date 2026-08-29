"""Strict world-graph capability contracts for SDK schema 4.0."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import CapabilityDescriptor, CapabilityExposure, CapabilityInputBinding


def _capability(**overrides):
    payload = {
        "id": "shipping.create",
        "title": "Create shipment",
        "description": "Create one shipment after an exact preview.",
        "effect": "external_write",
        "tool": "create_shipment",
        "requirements": {
            "authority": "write_external",
            "audience": ["private_internal", "team_internal"],
            "task_context": "optional",
        },
        "exposure": "model",
        "inputs": [
            {
                "kind": "value",
                "semantic_field": "recipient",
                "argument_name": "recipient",
                "sensitivity": "personal",
                "accepted_origins": ["current_user"],
            }
        ],
    }
    payload.update(overrides)
    return payload


def _safety_contracts():
    return {
        "prepared_action": {
            "preview_argument": "preview_only",
            "preview_value": True,
            "execute_value": False,
            "ttl_seconds": 3600,
        },
        "idempotency": {
            "argument_name": "idempotency_key",
            "required_for_execution": True,
        },
        "completion": {"receipts": ["shipping.shipment.created"]},
    }


def test_model_capability_requires_explicit_model_exposure():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(
            effect="read",
            produces=[
                {
                    "result_path": ".shipment",
                    "resource_type": "mrw.shipment",
                    "output_name": "shipment",
                }
            ],
        )
    )
    assert descriptor.exposure == CapabilityExposure.MODEL
    assert descriptor.non_callable_reason is None


def test_missing_exposure_is_rejected():
    payload = _capability(
        effect="read",
        produces=[
            {
                "result_path": ".shipment",
                "resource_type": "mrw.shipment",
                "output_name": "shipment",
            }
        ],
    )
    payload.pop("exposure")
    with pytest.raises(ValidationError, match="exposure"):
        CapabilityDescriptor.model_validate(payload)


@pytest.mark.parametrize("exposure", ["host", "admin"])
def test_non_model_exposure_requires_reason(exposure):
    with pytest.raises(ValidationError, match="non_callable_reason"):
        CapabilityDescriptor.model_validate(_capability(exposure=exposure))


def test_removed_model_callable_field_is_rejected():
    with pytest.raises(ValidationError, match="model_callable"):
        CapabilityDescriptor.model_validate(_capability(model_callable=True))


def test_deprecated_exposure_is_rejected():
    with pytest.raises(ValidationError, match="exposure"):
        CapabilityDescriptor.model_validate(_capability(exposure="deprecated"))


def test_model_selectable_external_write_requires_all_safety_contracts():
    with pytest.raises(ValidationError, match="prepared_action"):
        CapabilityDescriptor.model_validate(_capability())

    descriptor = CapabilityDescriptor.model_validate(
        _capability(**_safety_contracts())
    )
    assert descriptor.prepared_action.preview_argument == "preview_only"
    assert descriptor.idempotency.required_for_execution is True
    assert descriptor.completion.receipts == ["shipping.shipment.created"]


def test_host_external_write_remains_valid_without_prepared_contract():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(
            exposure="host",
            requirements={
                "authority": "write_external",
                "audience": ["private_internal", "team_internal"],
                "task_context": "required",
            },
            non_callable_reason={
                "code": "prepared_execution_only",
                "safe_summary": "Execution is restricted to the prepared-action host.",
            },
        )
    )
    assert descriptor.exposure == CapabilityExposure.HOST


def test_task_context_defaults_to_optional_for_every_capability():
    payload = _capability(
        effect="read",
        produces=[
            {
                "result_path": ".shipment",
                "resource_type": "mrw.shipment",
                "output_name": "shipment",
            }
        ],
    )
    payload["requirements"].pop("task_context")

    descriptor = CapabilityDescriptor.model_validate(payload)

    assert descriptor.requirements.task_context == "optional"


def test_task_context_accepts_forbidden():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(
            effect="read",
            requirements={
                "authority": "read",
                "audience": ["private_internal"],
                "task_context": "forbidden",
            },
            produces=[
                {
                    "result_path": ".shipment",
                    "resource_type": "mrw.shipment",
                    "output_name": "shipment",
                }
            ],
        )
    )

    assert descriptor.requirements.task_context == "forbidden"


def test_sdk_leaves_task_owned_resource_promotion_to_registry():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(
            effect="read",
            consumes=[{"name": "action", "resource_type": "prepared_action"}],
            produces=[
                {
                    "result_path": ".shipment",
                    "resource_type": "mrw.shipment",
                    "output_name": "shipment",
                }
            ],
        )
    )

    assert descriptor.requirements.task_context == "optional"


def test_model_read_requires_typed_output():
    with pytest.raises(ValidationError, match="declared outputs"):
        CapabilityDescriptor.model_validate(_capability(effect="read", inputs=[]))


def test_unknown_prepared_action_adapter_is_rejected():
    contracts = _safety_contracts()
    contracts["prepared_action"]["adapter"] = "plugin.argument_toggle"
    with pytest.raises(ValidationError, match="adapter"):
        CapabilityDescriptor.model_validate(_capability(**contracts))


def test_personal_input_provenance_is_independent_from_sensitivity():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(
            inputs=[
                {
                    "kind": "value",
                    "semantic_field": "recipient",
                    "argument_name": "recipient",
                    "sensitivity": "personal",
                    "requires_provenance": True,
                    "accepted_origins": ["world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "body",
                    "argument_name": "body",
                    "sensitivity": "personal",
                    "requires_provenance": False,
                    "accepted_origins": ["current_user", "world_resource"],
                },
            ],
            **_safety_contracts(),
        )
    )

    assert descriptor.inputs[0].requires_provenance is True
    assert descriptor.inputs[1].requires_provenance is False


def test_resource_input_rejects_redundant_requires_provenance():
    payload = _capability(
        effect="read",
        inputs=[
            {
                "kind": "resource",
                "semantic_field": "source_ref",
                "argument_name": "source_ref",
                "resource_type": "email_message",
                "requires_provenance": True,
                "accepted_origins": ["world_resource"],
            }
        ],
        produces=[
            {
                "result_path": ".message",
                "resource_type": "email_message",
                "output_name": "message",
            }
        ],
    )

    with pytest.raises(ValidationError, match="already carry world_resource provenance"):
        CapabilityDescriptor.model_validate(payload)


def test_resource_input_requires_world_resource_origin():
    with pytest.raises(ValidationError, match="world_resource"):
        CapabilityInputBinding.model_validate(
            {
                "kind": "resource",
                "semantic_field": "source_ref",
                "argument_name": "source_ref",
                "resource_type": "email_message",
                "accepted_origins": ["current_user"],
            }
        )
