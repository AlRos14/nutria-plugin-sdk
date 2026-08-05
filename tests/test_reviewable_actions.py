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
        "prepare_tool": {"name": "prepare_reply", "external_write": False},
        "execute_tool": "send_reply",
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


def _manifest(**overrides):
    data = {
        "schema_version": "1.1",
        "id": "email-plugin",
        "name": "Email",
        "version": "1.0.0",
        "description": "Email delivery",
        "author": "Nutria",
        "runtime_types": ["remote_mcp"],
        "reviewable_actions": [_contract()],
    }
    data.update(overrides)
    return data


def test_contract_has_stable_fingerprint():
    contract = ReviewableActionContract.model_validate(_contract())
    assert contract.prepare_tool is not None
    assert contract.prepare_tool.name == "prepare_reply"
    assert contract.fingerprint() == ReviewableActionContract.model_validate(
        _contract()
    ).fingerprint()


def test_schema_10_is_rejected():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_manifest(schema_version="1.0", reviewable_actions=[]))


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
        {"prepare_tool": {"name": "send_reply", "external_write": False}},
        {"prepare_tool": {"name": "prepare_reply", "external_write": True}},
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
