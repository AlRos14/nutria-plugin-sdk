"""Provider-neutral operations on one attribute across a hierarchical entity.

An entity may own child entities (variants of an item, ads of a campaign, establishments of an
organization, child resources of a configuration). The Agent reasons about *entity, children,
attribute, value and scope*; the provider implementation decides how that is physically stored.

Semantics (the whole model; there is no durable inheritance):

* ``self``                the value applies to the entity itself only;
* ``selected_children``   the value applies to exactly the listed children;
* ``all_children``        the value applies to every relevant child of the entity. Any value a child held
                          before, including a special one set by an earlier operation, is replaced.

``overrides`` are explicit exceptions of THIS operation only (``all_children`` with a different value for
named children). They describe the operation; they create no lasting protection against a later global
operation. The result of an operation is its *effective state*; how a provider stores it (for example a blank
parent that carries nothing while every child carries the value) is factual metadata, never the canonical
representation.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class OperationScope(str, Enum):
    SELF = "self"
    SELECTED_CHILDREN = "selected_children"
    ALL_CHILDREN = "all_children"


_ATTRIBUTE = r"^[a-z][a-z0-9_.-]{0,127}$"
_REF = {"min_length": 1, "max_length": 512}


class ChildValue(BaseModel):
    """An explicit value for one child, valid for the current operation only."""

    target_ref: str = Field(..., **_REF)
    value: Any

    model_config = {"extra": "forbid"}


class AttributeOperation(BaseModel):
    """One requested assignment of ``attribute`` over a scope of a hierarchical entity."""

    attribute: str = Field(..., pattern=_ATTRIBUTE)
    value: Any
    scope: OperationScope
    targets: list[str] = Field(default_factory=list)
    overrides: list[ChildValue] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _coherent(self) -> "AttributeOperation":
        if self.scope == OperationScope.SELECTED_CHILDREN:
            if not self.targets:
                raise ValueError("selected_children requires the exact child targets")
        elif self.targets:
            raise ValueError("targets are only meaningful for selected_children")
        if len(self.targets) != len(set(self.targets)):
            raise ValueError("targets must not repeat")
        if self.overrides and self.scope != OperationScope.ALL_CHILDREN:
            raise ValueError("overrides are exceptions of an all_children operation")
        override_refs = [item.target_ref for item in self.overrides]
        if len(override_refs) != len(set(override_refs)):
            raise ValueError("overrides must not repeat a child")
        return self


class HierarchicalAttributeDescriptor(BaseModel):
    """What a capability can do with one attribute over a hierarchy (declared per attribute)."""

    attribute: str = Field(..., pattern=_ATTRIBUTE)
    scopes: list[OperationScope] = Field(..., min_length=1)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _unique_scopes(self) -> "HierarchicalAttributeDescriptor":
        if len(self.scopes) != len(set(self.scopes)):
            raise ValueError("scopes must not repeat")
        return self


class EffectiveAttributeState(BaseModel):
    """Canonical readback of one attribute over a hierarchy.

    ``values`` is the effective state (what each entity effectively has). ``provider_representation`` is
    observability only: how the provider physically holds it, per entity, when that differs from the
    effective state (for example ``{"<entity>": None}``). It never replaces ``values``.
    """

    attribute: str = Field(..., pattern=_ATTRIBUTE)
    entity_ref: str = Field(..., **_REF)
    values: dict[str, Any]
    provider_representation: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


def apply_attribute_operation(
    operation: AttributeOperation,
    *,
    entity_ref: str,
    children: Mapping[str, Any],
    entity_value: Any = None,
) -> dict[str, Any]:
    """The effective state of ``entity_ref`` and its ``children`` after ``operation`` (pure, reference).

    Providers implement the same result physically; this function is the contract oracle.
    """
    effective: dict[str, Any] = {entity_ref: entity_value, **dict(children)}
    if operation.scope == OperationScope.SELF:
        effective[entity_ref] = operation.value
        return effective
    unknown = [r for r in operation.targets if r not in children]
    unknown += [item.target_ref for item in operation.overrides if item.target_ref not in children]
    if unknown:
        raise ValueError(f"unknown child targets: {sorted(set(unknown))}")
    if operation.scope == OperationScope.SELECTED_CHILDREN:
        for ref in operation.targets:
            effective[ref] = operation.value
        return effective
    for ref in children:
        effective[ref] = operation.value
    for item in operation.overrides:
        effective[item.target_ref] = item.value
    return effective
