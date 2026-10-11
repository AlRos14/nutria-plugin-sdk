"""Contract tests for hierarchical attribute operations (independent of any provider or domain)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutria_plugin import (
    AttributeOperation,
    ChildValue,
    EffectiveAttributeState,
    HierarchicalAttributeDescriptor,
    OperationScope,
    apply_attribute_operation,
)
from nutria_plugin.operation_facts import OperationFacts, TargetFact

PARENT = "Parent"
CHILDREN = {"A": "V", "B": "V", "C": "V"}


def apply(op: AttributeOperation, children=None, entity_value=None):
    return apply_attribute_operation(
        op, entity_ref=PARENT, children=children or CHILDREN, entity_value=entity_value
    )


def test_global_assignment_reaches_every_child():
    op = AttributeOperation(attribute="attribute_x", value="V2", scope=OperationScope.ALL_CHILDREN)
    result = apply(op, {"A": None, "B": None, "C": None})
    assert [result[c] for c in "ABC"] == ["V2", "V2", "V2"]


def test_specific_child_assignment_changes_only_that_child():
    op = AttributeOperation(
        attribute="attribute_x", value="X", scope=OperationScope.SELECTED_CHILDREN, targets=["B"]
    )
    result = apply(op)
    assert (result["A"], result["B"], result["C"]) == ("V", "X", "V")
    assert result[PARENT] is None


def test_current_operation_override_is_an_exception_of_this_operation_only():
    op = AttributeOperation(
        attribute="attribute_x",
        value="V",
        scope=OperationScope.ALL_CHILDREN,
        overrides=[ChildValue(target_ref="B", value="X")],
    )
    result = apply(op, {"A": None, "B": None, "C": None})
    assert (result["A"], result["B"], result["C"]) == ("V", "X", "V")


def test_later_global_assignment_replaces_a_prior_child_special_value():
    existing = {"A": "V", "B": "X", "C": "V"}
    op = AttributeOperation(attribute="attribute_x", value="Y", scope=OperationScope.ALL_CHILDREN)
    result = apply(op, existing)
    assert (result["A"], result["B"], result["C"]) == ("Y", "Y", "Y")


def test_operation_on_self_leaves_children_untouched():
    op = AttributeOperation(attribute="attribute_x", value="S", scope=OperationScope.SELF)
    result = apply(op)
    assert result[PARENT] == "S" and [result[c] for c in "ABC"] == ["V", "V", "V"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"scope": OperationScope.SELECTED_CHILDREN},
        {"scope": OperationScope.SELF, "targets": ["A"]},
        {"scope": OperationScope.SELECTED_CHILDREN, "targets": ["A"], "overrides": [ChildValue(target_ref="A", value=1)]},
        {"scope": OperationScope.ALL_CHILDREN, "overrides": [ChildValue(target_ref="A", value=1), ChildValue(target_ref="A", value=2)]},
        {"scope": OperationScope.SELECTED_CHILDREN, "targets": ["A", "A"]},
    ],
)
def test_incoherent_operations_are_rejected(kwargs):
    with pytest.raises(ValidationError):
        AttributeOperation(attribute="attribute_x", value=1, **kwargs)


def test_unknown_children_are_rejected():
    op = AttributeOperation(
        attribute="attribute_x", value=1, scope=OperationScope.SELECTED_CHILDREN, targets=["Z"]
    )
    with pytest.raises(ValueError):
        apply(op)


def test_contract_vocabulary_is_domain_neutral():
    import nutria_plugin.hierarchy as module

    source = open(module.__file__, encoding="utf-8").read().lower()
    for word in ("woocommerce", "product", "variation", "regular_price", "price"):
        assert word not in source


def test_attribute_declarations_are_per_attribute_and_validated():
    ok = HierarchicalAttributeDescriptor(
        attribute="attribute_x", scopes=[OperationScope.ALL_CHILDREN, OperationScope.SELECTED_CHILDREN]
    )
    assert ok.attribute == "attribute_x"
    other = HierarchicalAttributeDescriptor(attribute="attribute_y", scopes=[OperationScope.SELF])
    assert other.scopes == [OperationScope.SELF]  # different attributes, different semantics
    with pytest.raises(ValidationError):
        HierarchicalAttributeDescriptor(attribute="attribute_x", scopes=[])
    with pytest.raises(ValidationError):
        HierarchicalAttributeDescriptor(
            attribute="attribute_x", scopes=[OperationScope.SELF, OperationScope.SELF]
        )


def test_effective_readback_keeps_provider_representation_as_metadata():
    state = EffectiveAttributeState(
        attribute="attribute_x",
        entity_ref=PARENT,
        values={"A": "V", "B": "V", "C": "V"},
        provider_representation={PARENT: None},
    )
    assert set(state.values) == {"A", "B", "C"} and state.provider_representation == {PARENT: None}


def test_operation_facts_can_report_effective_values_without_concluding_completion():
    facts = OperationFacts(
        provider_outcome="succeeded",
        mutation="confirmed",
        verification="verified",
        targets=[
            TargetFact(
                target_ref=ref,
                outcome="succeeded",
                verified_fields=["attribute_x"],
                effective_values={"attribute_x": "V"},
            )
            for ref in ("A", "B", "C")
        ]
        + [
            TargetFact(
                target_ref=PARENT,
                outcome="succeeded",
                provider_representation={"attribute_x": None},
            )
        ],
    )
    assert facts.targets[-1].provider_representation == {"attribute_x": None}
    assert not hasattr(facts, "completed")


def test_capability_descriptor_accepts_declared_hierarchical_attributes_and_stays_compatible():
    from nutria_plugin import CapabilityDescriptor

    base = {
        "id": "demo.set_attribute",
        "title": "Set attribute",
        "description": "Sets an attribute over a hierarchy.",
        "domains": ["products"],
        "effect": "write",
        "effect_scope": "internal_state",
        "tool": "set_attribute",
        "inputs": [
            {
                "kind": "value",
                "semantic_field": "attribute_x",
                "argument_name": "attribute_x",
                "data_class": "non_personal",
                "accepted_origins": ["current_user"],
            }
        ],
        "requirements": {"authority": "write_internal", "audience": ["private_internal"]},
        "exposure": "model",
        "completion": {"evidence": "none"},
    }
    without = CapabilityDescriptor.model_validate(base)
    assert without.hierarchical_attributes == []
    declared = CapabilityDescriptor.model_validate(
        {**base, "hierarchical_attributes": [{"attribute": "attribute_x", "scopes": ["all_children", "self"]}]}
    )
    assert declared.hierarchical_attributes[0].scopes == [OperationScope.ALL_CHILDREN, OperationScope.SELF]
    with pytest.raises(ValidationError):
        CapabilityDescriptor.model_validate(
            {**base, "hierarchical_attributes": [
                {"attribute": "attribute_x", "scopes": ["self"]},
                {"attribute": "attribute_x", "scopes": ["all_children"]},
            ]}
        )
