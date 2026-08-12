"""Capability exposure and effect-safety contracts introduced in SDK 0.2.2."""

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


def test_legacy_model_capability_gets_explicit_model_exposure():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(effect="read", model_callable=True)
    )
    assert descriptor.exposure == CapabilityExposure.MODEL
    assert descriptor.non_callable_reason is None


def test_legacy_non_callable_capability_gets_safe_host_projection():
    descriptor = CapabilityDescriptor.model_validate(
        _capability(model_callable=False)
    )
    assert descriptor.exposure == CapabilityExposure.HOST
    assert descriptor.non_callable_reason.code == "legacy_host_only"


@pytest.mark.parametrize("exposure", ["host", "admin", "deprecated"])
def test_non_model_exposure_requires_reason(exposure):
    with pytest.raises(ValidationError, match="non_callable_reason"):
        CapabilityDescriptor.model_validate(
            _capability(exposure=exposure, model_callable=False)
        )


def test_model_exposure_requires_model_callable():
    with pytest.raises(ValidationError, match="model_callable"):
        CapabilityDescriptor.model_validate(
            _capability(exposure="model", model_callable=False)
        )


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
            model_callable=False,
            non_callable_reason={
                "code": "prepared_execution_only",
                "safe_summary": "Execution is restricted to the prepared-action host.",
            },
        )
    )
    assert descriptor.exposure == CapabilityExposure.HOST
