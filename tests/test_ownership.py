import pytest

from nutria_plugin import ConversationOwnership, OwnerKind, ownership_from_event_payload


def test_structured_payload_is_read():
    owner = ownership_from_event_payload(
        {"conversation_ownership": {"owner_kind": "agent", "owner_ref": "lia", "locked": False}}
    )
    assert owner.owner_kind is OwnerKind.AGENT and owner.owner_ref == "lia"


@pytest.mark.parametrize(
    "payload,locked",
    [
        ({"ownership_state": "human_owned", "reply_blocked": True}, False),
        ({"owner_state": "locked"}, True),
        ({"human_owned": True}, False),
    ],
)
def test_legacy_keys_map_to_human(payload, locked):
    owner = ownership_from_event_payload(payload)
    assert owner.owner_kind is OwnerKind.HUMAN
    assert owner.locked is locked


def test_unknown_or_silent_payloads():
    assert ownership_from_event_payload(None) is None
    assert ownership_from_event_payload({"preview": "hola"}) is None
    assert ownership_from_event_payload({"ownership_state": "agent_owned"}).owner_kind is OwnerKind.CUSTOMER_SERVICE


def test_priority_and_locks():
    customer_service = ConversationOwnership()
    agent = ConversationOwnership(owner_kind=OwnerKind.AGENT, owner_ref="lia")
    human = ConversationOwnership(owner_kind=OwnerKind.HUMAN, owner_ref="ana")
    locked_agent = ConversationOwnership(owner_kind=OwnerKind.AGENT, owner_ref="lia", locked=True)

    assert customer_service.may_be_taken_by(OwnerKind.AGENT, ref="lia")
    assert not agent.may_be_taken_by(OwnerKind.CUSTOMER_SERVICE)
    assert agent.may_be_taken_by(OwnerKind.AGENT, ref="lia")
    assert not agent.may_be_taken_by(OwnerKind.AGENT, ref="marcos")
    assert agent.may_be_taken_by(OwnerKind.HUMAN)
    assert not human.may_be_taken_by(OwnerKind.AGENT, ref="lia")
    assert not locked_agent.may_be_taken_by(OwnerKind.AGENT, ref="lia")
    assert locked_agent.may_be_taken_by(OwnerKind.HUMAN)
    assert not human.agents_may_reply and not locked_agent.agents_may_reply and agent.agents_may_reply
