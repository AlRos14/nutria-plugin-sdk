"""Contract vNext (schema 6.0): effect scope, explicit completion, data classes, facts."""

from __future__ import annotations

import copy
import io
import json
import zipfile

import pytest
from pydantic import ValidationError

from nutria_plugin import (
    CapabilityDescriptor,
    MCPResultContractError,
    OperationFacts,
    PluginManifest,
    parse_skill_frontmatter,
    validate_capability_result,
    validate_zip,
)
from nutria_plugin.migrate import migrate_manifest_5_to_6
from .test_capability_contracts import _capability, _safety_contracts

TERMINAL = {
    "id": "agent.terminal.run",
    "title": "Run a terminal command",
    "description": "Run a command in the agent-local sandbox.",
    "domains": ["products"],
    "effect": "write",
    "effect_scope": "agent_local",
    "tool": "run_terminal",
    "requirements": {"authority": "write_internal", "audience": ["team_internal"]},
    "exposure": "model",
    "inputs": [
        {
            "kind": "value",
            "semantic_field": "command",
            "argument_name": "command",
            "data_class": "non_personal",
            "accepted_origins": ["current_user"],
        }
    ],
    "completion": {"evidence": "none"},
}


def test_terminal_is_a_write_without_completion_expectation():
    descriptor = CapabilityDescriptor.model_validate(TERMINAL)

    assert descriptor.effect.value == "write"
    assert descriptor.effect_scope.value == "agent_local"
    assert descriptor.completion.evidence == "none"


def test_non_read_capability_must_declare_completion_explicitly():
    payload = {k: v for k, v in TERMINAL.items() if k != "completion"}

    with pytest.raises(ValidationError, match="must declare completion explicitly"):
        CapabilityDescriptor.model_validate(payload)


def test_agent_local_capability_cannot_declare_completion_evidence():
    payload = {
        **TERMINAL,
        "completion": {"evidence": "declared", "receipts": ["x.done"], "basis": "provider_outcome"},
    }

    with pytest.raises(ValidationError, match="agent_local"):
        CapabilityDescriptor.model_validate(payload)


def test_read_capability_does_not_declare_completion():
    payload = _capability(
        effect="read",
        completion={"evidence": "none"},
        produces=[
            {
                "result_path": ".s",
                "resource_type": "mrw.shipment",
                "output_name": "s",
                "data_class": "non_personal",
            }
        ],
    )

    with pytest.raises(ValidationError, match="must not declare completion"):
        CapabilityDescriptor.model_validate(payload)


def test_internal_state_write_may_complete_an_objective_via_declared_evidence():
    payload = {
        **TERMINAL,
        "id": "agent.notebook.write",
        "effect_scope": "internal_state",
        "completion": {
            "evidence": "declared",
            "receipts": ["notebook.entry.saved"],
            "basis": "confirmed_mutation",
        },
    }

    assert CapabilityDescriptor.model_validate(payload).completion.evidence == "declared"


def test_model_world_write_requires_declared_completion_and_idempotency():
    base = _capability(**_safety_contracts())
    CapabilityDescriptor.model_validate(base)

    for broken in (
        {**base, "completion": {"evidence": "none"}},
        {k: v for k, v in base.items() if k != "idempotency"},
    ):
        with pytest.raises(ValidationError):
            CapabilityDescriptor.model_validate(broken)


def test_external_write_must_land_in_the_world_scope():
    payload = _capability(**_safety_contracts(), effect_scope="internal_state")

    with pytest.raises(ValidationError, match="effect_scope 'world'"):
        CapabilityDescriptor.model_validate(payload)


def test_declared_completion_needs_receipts_and_basis():
    for completion in (
        {"evidence": "declared", "basis": "provider_outcome"},
        {"evidence": "declared", "receipts": ["a.b"]},
        {"evidence": "none", "receipts": ["a.b"]},
    ):
        with pytest.raises(ValidationError):
            CapabilityDescriptor.model_validate({**TERMINAL, "completion": completion})


def test_data_class_is_required_closed_and_replaces_sensitivity():
    payload = copy.deepcopy(TERMINAL)
    payload["inputs"][0].pop("data_class")
    with pytest.raises(ValidationError, match="data_class"):
        CapabilityDescriptor.model_validate(payload)

    payload["inputs"][0]["data_class"] = "personal_identifier"
    CapabilityDescriptor.model_validate(payload)
    payload["inputs"][0]["data_class"] = "secret_sauce"
    with pytest.raises(ValidationError):
        CapabilityDescriptor.model_validate(payload)
    payload["inputs"][0]["data_class"] = "non_personal"
    payload["inputs"][0]["sensitivity"] = "safe"
    with pytest.raises(ValidationError, match="sensitivity"):
        CapabilityDescriptor.model_validate(payload)


def test_all_six_data_classes_are_available():
    from nutria_plugin import DataClass

    assert {item.value for item in DataClass} == {
        "non_personal",
        "business_resource_identifier",
        "operational_identifier",
        "personal_identifier",
        "personal_content",
        "special_category",
    }


# --- OperationFacts and the SDK-side proof that declared completion is producible ---------


def _capability_dict(**completion):
    return {
        "effect": "external_write",
        "completion": {
            "evidence": "declared",
            "receipts": ["email.sent"],
            "basis": "delivery_confirmation",
            "targets": "single",
            **completion,
        },
    }


def test_confirmed_mutation_must_carry_every_declared_receipt():
    capability = _capability_dict()
    delivered = {
        "operation_facts": {
            "provider_outcome": "succeeded",
            "mutation": "confirmed",
            "phase": "delivered",
            "receipt_kinds": ["email.sent"],
        }
    }
    validate_capability_result(capability, structured_content=delivered)

    missing = json.loads(json.dumps(delivered))
    missing["operation_facts"]["receipt_kinds"] = []
    with pytest.raises(MCPResultContractError, match="missing declared receipts"):
        validate_capability_result(capability, structured_content=missing)


def test_two_phase_delivery_is_not_confirmed_at_acceptance():
    capability = _capability_dict()
    accepted = {
        "operation_facts": {
            "provider_outcome": "accepted",
            "mutation": "confirmed",
            "phase": "accepted",
            "receipt_kinds": ["email.sent"],
        }
    }

    with pytest.raises(MCPResultContractError, match="delivery_confirmation"):
        validate_capability_result(capability, structured_content=accepted)


def test_capability_without_completion_evidence_cannot_emit_receipts():
    capability = {"effect": "write", "completion": {"evidence": "none"}}
    facts = {"operation_facts": {"provider_outcome": "succeeded", "receipt_kinds": ["x.done"]}}

    with pytest.raises(MCPResultContractError, match="no completion evidence"):
        validate_capability_result(capability, structured_content=facts)


def test_operation_facts_reject_incoherent_combinations():
    with pytest.raises(ValidationError):
        OperationFacts(provider_outcome="failed", mutation="confirmed")
    with pytest.raises(ValidationError):
        OperationFacts(provider_outcome="succeeded", verification="verified")
    with pytest.raises(ValidationError):
        OperationFacts(provider_outcome="succeeded", partial=True)


# --- skills and migration -------------------------------------------------------------------


def test_skill_frontmatter_rejects_legacy_triggers():
    with pytest.raises(ValidationError, match="triggers"):
        parse_skill_frontmatter("---\nname: a-skill\ndescription: d\ntriggers: [x]\n---\nBody")
    assert parse_skill_frontmatter("---\nname: a-skill\ndescription: d\n---\nBody").name == "a-skill"


def test_bundle_validation_reports_skills_with_triggers():
    from .test_bundle import VALID_MANIFEST

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("plugin.json", VALID_MANIFEST)
        archive.writestr(
            "skills/a/SKILL.md", "---\nname: a\ndescription: d\ntriggers: [x]\n---\nBody"
        )

    errors = validate_zip(buffer.getvalue())

    assert any("triggers" in error for error in errors)


def test_migration_5_to_6_is_conservative_and_reports_judgement_calls():
    legacy = {
        "schema_version": "5.0",
        "capabilities": [
            {
                "id": "x.send",
                "effect": "external_write",
                "connection_id": "x",
                "completion": {"receipts": ["x.sent"]},
                "inputs": [{"semantic_field": "to", "sensitivity": "personal"}],
                "produces": [{"output_name": "msg"}],
            },
            {"id": "x.read", "effect": "read", "completion": {"receipts": ["ignored"]}},
        ],
    }

    migrated, review = migrate_manifest_5_to_6(legacy)

    send, read = migrated["capabilities"]
    assert migrated["schema_version"] == "6.0"
    assert send["effect_scope"] == "world"
    assert send["completion"]["evidence"] == "declared"
    assert send["inputs"][0]["data_class"] == "personal_identifier"
    assert "sensitivity" not in send["inputs"][0]
    assert "completion" not in read
    assert any("basis defaulted" in item for item in review)
    assert any("personal -> personal_identifier" in item for item in review)


def test_manifest_5_0_is_rejected_with_schema_error():
    with pytest.raises(ValidationError, match="schema_version"):
        PluginManifest.model_validate({"schema_version": "5.0"})
