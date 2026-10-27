"""Conversation ownership: who answers an outside person right now.

A channel plugin that talks to outside people (WhatsApp, email, chat widgets) reports, with each inbound
event, who owns the conversation. A host resolves the answering agent from it. One definition, so every
plugin and every host agree on the words.

Priority, strongest first: ``human`` > ``agent`` > ``customer_service``. A weaker owner never takes a
conversation from a stronger one. A lock (set by a person) holds the conversation against every agent.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OwnerKind(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    CUSTOMER_SERVICE = "customer_service"


OWNER_PRIORITY: dict[OwnerKind, int] = {
    OwnerKind.HUMAN: 3,
    OwnerKind.AGENT: 2,
    OwnerKind.CUSTOMER_SERVICE: 1,
}

# States older plugins already send in the event payload (``owner_state`` / ``ownership_state``).
_LEGACY_HUMAN_STATES = frozenset({"human_owned", "locked", "human"})


class ConversationOwnership(BaseModel):
    """Who owns one conversation with one contact on one channel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    owner_kind: OwnerKind = OwnerKind.CUSTOMER_SERVICE
    owner_ref: str | None = Field(
        default=None,
        description="Agent id when owner_kind is 'agent'; the person's id when 'human'; empty otherwise.",
    )
    locked: bool = Field(
        default=False,
        description="A person locked the conversation: no agent replies, whatever the owner kind.",
    )
    reason: str | None = None

    @property
    def priority(self) -> int:
        return OWNER_PRIORITY[self.owner_kind] + (10 if self.locked else 0)

    @property
    def agents_may_reply(self) -> bool:
        return self.owner_kind != OwnerKind.HUMAN and not self.locked

    def may_be_taken_by(self, kind: OwnerKind, *, ref: str | None = None) -> bool:
        """Whether a new owner of ``kind`` may take this conversation.

        Equal rank may only re-take its own conversation (same ``ref``); a locked conversation is taken
        only by a human.
        """
        if self.locked:
            return kind == OwnerKind.HUMAN
        if OWNER_PRIORITY[kind] > OWNER_PRIORITY[self.owner_kind]:
            return True
        return kind == self.owner_kind and (ref or None) == (self.owner_ref or None)


def ownership_from_event_payload(payload: Mapping[str, Any] | None) -> ConversationOwnership | None:
    """Read ownership from an external-channel event payload.

    Prefers the structured ``conversation_ownership`` object. Falls back to the keys older plugins send
    (``ownership_state`` / ``owner_state`` / ``human_owned`` / ``reply_blocked``) so they keep working.
    Returns ``None`` when the payload says nothing about ownership.
    """
    if not isinstance(payload, Mapping):
        return None
    structured = payload.get("conversation_ownership")
    if isinstance(structured, Mapping):
        return ConversationOwnership.model_validate(dict(structured))
    state = str(payload.get("ownership_state") or payload.get("owner_state") or "").strip().lower()
    human = bool(payload.get("human_owned")) or state in _LEGACY_HUMAN_STATES
    if human:
        return ConversationOwnership(
            owner_kind=OwnerKind.HUMAN,
            locked=state == "locked",
            reason=str(payload.get("block_reason") or "") or None,
        )
    if state or "reply_blocked" in payload:
        return ConversationOwnership(owner_kind=OwnerKind.CUSTOMER_SERVICE)
    return None
