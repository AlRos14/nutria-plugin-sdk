"""A capability offered to an outside audience is pinned to the person the conversation is with."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import (
    CapabilityDescriptor,
    apply_conversation_scope,
    offered_to_outside_audience,
    scoped_argument,
)


def _read(
    audience=("private_internal", "public_customer"), inputs=None, data_class="personal_content"
):
    return {
        "id": "chat.recent",
        "title": "Recent messages",
        "description": "Recent messages of one chat.",
        "domains": ["whatsapp"],
        "effect": "read",
        "effect_scope": "world",
        "tool": "recent",
        "requirements": {"authority": "read", "audience": list(audience)},
        "exposure": "model",
        "produces": [
            {
                "result_path": ".messages",
                "resource_type": "whatsapp_message",
                "output_name": "messages",
                "many": True,
                "data_class": data_class,
            }
        ],
        "inputs": inputs
        if inputs is not None
        else [
            {
                "kind": "value",
                "semantic_field": "chat",
                "argument_name": "chat",
                "required": False,
                "data_class": "personal_identifier",
                "accepted_origins": ["current_user"],
                "scope": "conversation_contact",
            }
        ],
    }


def test_a_scoped_read_is_valid_and_names_its_argument():
    payload = _read()
    CapabilityDescriptor.model_validate(payload)

    assert scoped_argument(payload) == "chat" and offered_to_outside_audience(payload)


def test_the_contact_replaces_what_the_model_sent_or_left_empty():
    payload = _read()

    assert apply_conversation_scope(
        payload, {"chat": "34600000000", "limit": 5}, " 34611111111 "
    ) == {
        "chat": "34611111111",
        "limit": 5,
    }
    assert apply_conversation_scope(payload, {}, "34611111111") == {"chat": "34611111111"}


def test_a_capability_not_offered_to_the_outside_is_never_pinned():
    with pytest.raises(ValueError):
        apply_conversation_scope(_read(audience=("private_internal",)), {}, "34611111111")
    with pytest.raises(ValueError):
        apply_conversation_scope(_read(), {}, "  ")


def test_personal_content_for_the_outside_needs_a_scoped_input():
    with pytest.raises(ValidationError, match="scope an input"):
        CapabilityDescriptor.model_validate(_read(inputs=[]))


def test_another_person_identifying_input_is_refused_for_the_outside():
    other = {
        "kind": "value",
        "semantic_field": "recipient",
        "argument_name": "recipient",
        "data_class": "personal_identifier",
        "accepted_origins": ["current_user"],
    }
    scoped = _read()["inputs"][0]

    with pytest.raises(ValidationError, match="another person-identifying input"):
        CapabilityDescriptor.model_validate(_read(inputs=[scoped, other]))


def test_only_a_personal_identifier_value_can_be_scoped_and_only_one():
    base = _read()["inputs"][0]

    with pytest.raises(ValidationError, match="personal_identifier"):
        CapabilityDescriptor.model_validate(_read(inputs=[{**base, "data_class": "non_personal"}]))
    with pytest.raises(ValidationError, match="only one input"):
        CapabilityDescriptor.model_validate(
            _read(inputs=[base, {**base, "semantic_field": "peer", "argument_name": "peer"}])
        )


def test_a_write_cannot_be_scoped_or_offered_to_the_outside():
    payload = _read()
    payload.update(effect="write", effect_scope="internal_state", produces=[])
    payload["requirements"]["authority"] = "write_internal"

    with pytest.raises(ValidationError):
        CapabilityDescriptor.model_validate(payload)


def test_a_capability_without_scope_keeps_working_for_internal_audiences():
    CapabilityDescriptor.model_validate(_read(audience=("private_internal",), inputs=[]))
