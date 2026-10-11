# Capability author guide (schema 6.0)

This guide explains how to declare a capability so the Host can project, authorize, classify and disclose
it without any plugin-specific code. The authoritative field reference is [manifest.md](manifest.md);
migration from 5.0 is in [migration-6.0.md](migration-6.0.md).

## 1. Effect and effect scope

`effect` says whether something changes; `effect_scope` says where.

| `effect` | Meaning |
| --- | --- |
| `read` | Observes. Never declares `completion` or a world `prepared_action`. |
| `write` | Changes state. |
| `external_write` | Changes something outside the system (a message, a shipment). Scope must be `world`. |

| `effect_scope` | Use for |
| --- | --- |
| `agent_local` | Navigation, notes and other Principal-only state. No completion evidence. |
| `internal_state` | Nutria's own records. |
| `lifecycle` | Tasks, Interactions, PreparedActions. |
| `world` | Business systems and people. |

## 2. Completion

Every non-read capability declares `completion` explicitly:

```json
"completion": {
  "evidence": "declared",
  "receipts": ["shipment.created"],
  "basis": "provider_outcome",
  "targets": "single"
}
```

- `evidence: "none"` means the capability never proves completion; it must not list receipts, basis or targets.
- `basis` is how the provider proves it: `provider_outcome` (the provider's own success), `confirmed_mutation`,
  `verified_readback` (read the target back), `delivery_confirmation`, or `prepared_action` (a preview).
- `targets: "all_requested"` means every requested target must succeed; one success out of ten is `partial`.
- Model-selectable world writes must declare evidence and execution idempotency.

## 3. Operation facts (what handlers return)

Handlers report facts, never "completed". Return them in `structuredContent.operation_facts`:

```json
{
  "provider_outcome": "succeeded",
  "mutation": "confirmed",
  "verification": "verified",
  "receipt_kinds": ["shipment.created"],
  "targets": [{"target_ref": "SHP-1", "outcome": "succeeded"}],
  "provider_receipt": {"shipment_id": "SHP-1"}
}
```

The Host's ReceiptClassifier combines the declared contract and these facts into `completed`, `partial`,
`accepted`, `uncertain`, `failed`, `prepared`, `observed` or `not_applicable`. A write whose declared proof is
missing becomes `uncertain` and must be reconciled before any retry. `validate_operation_facts` rejects
contradictions (see the error table).

## 4. Data classification

Every input and output declares `data_class`:

| `data_class` | Examples |
| --- | --- |
| `non_personal` | Catalogue data, public web content |
| `business_resource_identifier` | Product or order ids |
| `operational_identifier` | Task, card or prepared-action handles |
| `personal_identifier` | Phone, email, address, recipient |
| `personal_content` | Message bodies, notes, documents about people |
| `special_category` | Health and other special categories |

The Host decides what reaches the inference provider from these classes, the tenant policy and the provider's
retention posture. It never guesses from field names, so classify honestly: an output that may carry
personal text is `personal_content`.

## 5. PreparedAction authoring

A model-selectable `external_write` must declare `prepared_action`. The model calls the preparation
capability, which must be pure and read-only and returns an exact preview. The Host freezes it and executes
the host-only execution capability only after authorization, with idempotency and the declared receipt.
Never re-resolve targets at execution time; execute exactly what the preview froze.

## 6. Hierarchical attribute operations

An entity can own child entities (variants of an item, ads of a campaign, establishments of an
organization, child resources of a configuration). The Agent decides **entity, children, attribute, value
and scope**; the provider materializes it. The contract is domain-neutral (`nutria_plugin.hierarchy`):

| Scope | Meaning |
| --- | --- |
| `self` | The value applies to the entity itself only. |
| `selected_children` | The value applies to exactly the listed children (`targets`). |
| `all_children` | The value applies to every relevant child. Any value a child held before, including a special one from an earlier operation, is replaced. |

* `overrides` are explicit exceptions of **this operation only** (`all_children` with other values for named
  children, e.g. creation "all at V, but B at X"). They are never remembered: a later `all_children`
  operation replaces them. Do not model durable inheritance.
* A capability declares what it supports per attribute with `hierarchical_attributes`
  (`[{"attribute": "...", "scopes": ["all_children", ...]}]`). Different attributes may declare different
  scopes. Only write capabilities may declare it; an attribute appears once.
* `apply_attribute_operation` is the reference semantics (the oracle for contract tests);
  `EffectiveAttributeState` is the canonical readback.
* **Readback is the effective state**, not the provider's physical layout. If the provider stores a value on
  the children and leaves the parent blank, report the effective values per child and put the physical
  parent value in `provider_representation` (observability only). The Agent must never need to know how the
  provider stores it.
* Facts stay facts: report per-child `TargetFact.effective_values` and, on the parent target,
  `provider_representation`. Completion is still concluded by the Host from the declared contract, and the
  Agent decides whether the Objective is complete.

## 7. Validation errors

| Error | Fix |
| --- | --- |
| `non-read capabilities must declare completion explicitly` | Add `completion` (`declared` or `none`). |
| `read capabilities observe; they must not declare completion` | Remove `completion` from reads. |
| `external_write capabilities must have effect_scope 'world'` | Set `effect_scope: "world"`. |
| `agent_local capabilities cannot declare completion evidence` | Use `evidence: "none"` or another scope. |
| `model-selectable world writes require declared completion evidence` | Declare receipts and basis. |
| `model-selectable world writes require execution idempotency` | Add `idempotency.required_for_execution`. |
| `model-selectable external writes require prepared_action` | Add a `prepared_action` contract. |
| `declared completion evidence requires receipts` / `... a basis` | Fill both. |
| `completion evidence 'none' must not declare receipts or basis` | Remove them. |
| `completion receipts must be stable lowercase identifiers` | Use ids like `email.reply.sent`. |
| `model-selectable reads require declared outputs` | Declare `produces` with `data_class`. |
| `model-selectable writes require declared inputs` | Declare every business input with `data_class`. |
| `a confirmed mutation cannot come from a failed or inapplicable outcome` | Fix the reported facts. |
| `verified requires a mutation fact other than none` | Report the mutation you verified. |
| `partial operations must report at least two targets` | Report per-target outcomes. |
| `verified operations cannot report mismatched fields` | Report `verification: "mismatch"`. |
