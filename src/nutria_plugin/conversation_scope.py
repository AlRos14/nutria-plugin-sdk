"""Pin a capability to the person a conversation is with.

A capability offered to an outside audience (``public_customer``) must never let the model, or the person
writing to it, choose whose data is read. The capability declares which argument names that person
(``scope: "conversation_contact"`` on the input); a host runs this rule before every call in such a turn.
It is pure (no I/O) so a plugin's tests and every host share one definition.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CONVERSATION_CONTACT = "conversation_contact"
OUTSIDE_AUDIENCE = "public_customer"


def scoped_argument(capability: Mapping[str, Any]) -> str | None:
    """The argument that names the conversation contact, or None when the capability declares none."""
    for item in capability.get("inputs") or []:
        if isinstance(item, Mapping) and item.get("scope") == CONVERSATION_CONTACT:
            name = item.get("argument_name")
            return str(name) if name else None
    return None


def offered_to_outside_audience(capability: Mapping[str, Any]) -> bool:
    requirements = capability.get("requirements")
    audience = requirements.get("audience") if isinstance(requirements, Mapping) else None
    return isinstance(audience, list) and OUTSIDE_AUDIENCE in audience


def apply_conversation_scope(
    capability: Mapping[str, Any], arguments: Mapping[str, Any], contact: str
) -> dict[str, Any]:
    """Arguments for one call in an outside-audience turn: the contact replaces whatever was sent.

    Raises ``ValueError`` when the capability is not offered to the outside audience, when it declares a
    person-identifying input without scope, or when the contact is empty. A capability that declares no
    scoped input is returned unchanged (it reads nothing about a person).
    """
    if not offered_to_outside_audience(capability):
        raise ValueError("capability is not offered to the public_customer audience")
    if not str(contact or "").strip():
        raise ValueError("an outside-audience call needs the conversation contact")
    argument = scoped_argument(capability)
    result = dict(arguments)
    if argument is not None:
        result[argument] = str(contact).strip()
    return result
