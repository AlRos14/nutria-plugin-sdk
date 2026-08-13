"""Strict world-graph capability contracts introduced in SDK 0.2.3."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import CapabilityDescriptor, CapabilityExposure


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
    }
    payload.update(overrides)
    return payload


def _safety_contracts():
    return {
        "prepared_action": {
            "preview_argument": "preview_only",
            "preview_value": True,
            "execute_value": False,
            "adapter": "exact_preview",
            "ttl_seconds": 3600,
            "merge_previews": True,
            "guard_mode": "pending_only",
            "argument_default": True,
        },
        "idempotency": {
            "argument_name": "idempotency_key",
            "required_for_execution": True,
        },
        "completion": {"receipts": ["shipping.shipment.created"]},
    }


def test_model_capability_requires_explicit_model_exposure():
    descriptor = CapabilityDescriptor.model_validate(_capability(effect="read"))
    assert descriptor.exposure == CapabilityExposure.MODEL
    assert descriptor.non_callable_reason is None


def test_missing_exposure_is_rejected():
    payload = _capability(effect="read")
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
    assert descriptor.prepared_action.adapter == "exact_preview"
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


def test_task_owned_resources_require_task_context():
    with pytest.raises(ValidationError, match="task_context=required"):
        CapabilityDescriptor.model_validate(
            _capability(
                effect="read",
                consumes=[{"name": "action", "resource_type": "prepared_action"}],
            )
        )
