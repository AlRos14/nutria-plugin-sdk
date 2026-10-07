"""Canonical facts a provider/handler reports about one operation.

Handlers and provider adapters *produce facts*. They never conclude ``completed``: the
host's ReceiptClassifier combines these facts with the capability's declared completion
contract. ``result.success`` only says the tool invocation itself ran.

A plugin reports facts under the ``operation_facts`` key of its structured result.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

OPERATION_FACTS_KEY = "operation_facts"

ProviderOutcome = Literal["accepted", "succeeded", "failed", "unknown", "not_applicable"]
MutationFact = Literal["none", "confirmed", "uncertain"]
VerificationFact = Literal["not_required", "verified", "mismatch", "pending", "unavailable"]
TargetOutcome = Literal["succeeded", "failed", "unknown", "skipped"]
OperationPhase = Literal["single", "accepted", "delivered"]


class TargetFact(BaseModel):
    """Outcome for one exact resource the operation was asked to affect."""

    target_ref: str = Field(..., min_length=1, max_length=512)
    outcome: TargetOutcome
    verified_fields: list[str] = Field(default_factory=list)
    mismatched_fields: list[str] = Field(default_factory=list)
    missing_effects: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class OperationFacts(BaseModel):
    provider_outcome: ProviderOutcome
    mutation: MutationFact = "none"
    verification: VerificationFact = "not_required"
    targets: list[TargetFact] = Field(default_factory=list)
    partial: bool = False
    phase: OperationPhase = "single"
    receipt_kinds: list[str] = Field(default_factory=list)
    prepared_action_id: str | None = None
    interaction_ref: str | None = None
    provider_receipt: dict[str, Any] | None = None
    reconciliation_ref: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _coherent(self) -> "OperationFacts":
        if self.mutation == "confirmed" and self.provider_outcome in {"failed", "not_applicable"}:
            raise ValueError("a confirmed mutation cannot come from a failed or inapplicable outcome")
        if self.verification == "verified" and self.mutation == "none":
            raise ValueError("verified requires a mutation fact other than none")
        if self.partial and len(self.targets) < 2:
            raise ValueError("partial operations must report at least two targets")
        if any(t.mismatched_fields for t in self.targets) and self.verification == "verified":
            raise ValueError("verified operations cannot report mismatched fields")
        return self


def extract_operation_facts(payload: Any) -> OperationFacts | None:
    """Return the facts embedded in a structured tool result, or ``None`` when absent."""
    if not isinstance(payload, Mapping) or OPERATION_FACTS_KEY not in payload:
        return None
    return OperationFacts.model_validate(payload[OPERATION_FACTS_KEY])
