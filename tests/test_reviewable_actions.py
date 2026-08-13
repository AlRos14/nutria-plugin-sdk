"""Contract validation tests for host-owned reviewable actions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import PluginManifest, ReviewableActionContract


def _contract(**overrides):
    data = {
        "id": "email-reply",
        "kind": "customer_message",
        "channel": "email",
        "modes": ["reply"],
        "connection_id": "email",
        "prepare_capability": "email.reply.prepare",
        "execute_capability": "email.send.reply",
        "argument_map": {
            "recipient": "recipient",
            "body": "body",
            "subject": "subject",
            "reply_target": "reply_to_message_id",
            "source_ref": "source_email_id",
            "source_fingerprint": "source_fingerprint",
            "idempotency_key": "idempotency_key",
        },
        "required_fields": ["recipient", "body"],
        "editable_fields": ["body", "subject"],
    }
    data.update(overrides)
    return data


def _capabilities():
    return [
        {
            "id": "email.reply.prepare",
            "title": "Prepare email reply",
            "description": "Resolve the source email envelope without writing.",
            "effect": "prepare",
            "tool": "prepare_email_reply",
            "connection_id": "email",
            "requirements": {
                "authority": "read",
                "audience": ["private_internal", "team_internal"],
                "task_context": "required",
            },
            "exposure": "model",
        },
        {
            "id": "email.send.reply",
            "title": "Send email reply",
            "description": "Deliver the exact approved email reply.",
            "effect": "external_write",
            "tool": "send_resolved_email_reply",
            "connection_id": "email",
            "consumes": [
                {"name": "action", "resource_type": "prepared_action"}
            ],
            "inputs": [
                {
                    "kind": "value",
                    "semantic_field": "recipient",
                    "argument_name": "recipient",
                    "sensitivity": "personal",
                    "accepted_origins": ["current_user", "world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "body",
                    "argument_name": "body",
                    "accepted_origins": ["current_user"],
                },
                {
                    "kind": "value",
                    "semantic_field": "subject",
                    "argument_name": "subject",
                    "required": False,
                    "accepted_origins": ["current_user", "world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "reply_target",
                    "argument_name": "reply_to_message_id",
                    "required": False,
                    "accepted_origins": ["world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "source_ref",
                    "argument_name": "source_email_id",
                    "required": False,
                    "accepted_origins": ["world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "source_fingerprint",
                    "argument_name": "source_fingerprint",
                    "required": False,
                    "accepted_origins": ["world_resource"],
                },
                {
                    "kind": "value",
                    "semantic_field": "idempotency_key",
                    "argument_name": "idempotency_key",
                    "accepted_origins": ["current_user"],
                },
            ],
            "requirements": {
                "authority": "write_external",
                "audience": ["private_internal", "team_internal"],
                "task_context": "required",
            },
            "exposure": "host",
            "non_callable_reason": {
                "code": "approval_required",
                "safe_summary": "The trusted host executes the reviewed reply.",
            },
            "reviewable_action_id": "email-reply",
        },
    ]


def _manifest(**overrides):
    data = {
        "schema_version": "3.0",
        "id": "email-plugin",
        "name": "Email",
        "version": "1.0.0",
        "description": "Email delivery",
        "author": "Nutria",
        "runtime_types": ["remote_mcp"],
        "capabilities": _capabilities(),
        "world_providers": [
            {
                "id": "email",
                "title": "Email",
                "description": "Authoritative mailbox resources.",
                "connection_id": "email",
                "resource_types": [
                    {
                        "id": "email_message",
                        "title": "Email message",
                        "description": "One stable email message.",
                        "identity_fields": ["id"],
                    }
                ],
            }
        ],
        "reviewable_actions": [_contract()],
    }
    data.update(overrides)
    return data


def test_contract_has_stable_fingerprint():
    contract = ReviewableActionContract.model_validate(_contract())
    assert contract.execute_capability == "email.send.reply"
    assert contract.prepare_capability == "email.reply.prepare"
    assert contract.fingerprint() == ReviewableActionContract.model_validate(
        _contract()
    ).fingerprint()


def test_schema_1_x_is_rejected():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_manifest(schema_version="1.1"))


def test_schema_version_is_required():
    payload = _manifest(reviewable_actions=[])
    payload.pop("schema_version")
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(payload)


def test_duplicate_contract_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        PluginManifest.model_validate(_manifest(reviewable_actions=[_contract(), _contract()]))


@pytest.mark.parametrize(
    "override",
    [
        {"modes": ["unknown"]},
        {"editable_fields": ["recipient"]},
        {"argument_map": {"recipient": "to", "body": "to"}},
        {"argument_map": {"body": "body"}},
        {"prepare_capability": "email.send.reply"},
    ],
)
def test_invalid_contracts_rejected(override):
    with pytest.raises(ValidationError):
        ReviewableActionContract.model_validate(_contract(**override))


def test_invalid_connection_and_argument_names_rejected():
    with pytest.raises(ValidationError):
        ReviewableActionContract.model_validate(_contract(connection_id="../email"))
    with pytest.raises(ValidationError):
        ReviewableActionContract.model_validate(
            _contract(argument_map={"recipient": "recipient", "body": "bad key"})
        )


def test_unknown_capability_reference_rejected():
    with pytest.raises(ValidationError, match="unknown execution capability"):
        PluginManifest.model_validate(
            _manifest(reviewable_actions=[_contract(execute_capability="email.send.missing")])
        )


def test_reviewable_external_write_must_be_host_only():
    capabilities = _capabilities()
    capabilities[1]["exposure"] = "model"
    capabilities[1].pop("non_callable_reason")
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_manifest(capabilities=capabilities))


def test_preparation_capability_must_be_pure_prepare():
    capabilities = _capabilities()
    capabilities[0]["effect"] = "write"
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_manifest(capabilities=capabilities))
