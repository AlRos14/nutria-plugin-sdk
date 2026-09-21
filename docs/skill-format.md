# SKILL.md format

A skill is domain guidance for the Agent. It tells the Agent when a capability
is useful and how to reason about the provider's business data. It is not a
runtime authority declaration or an execution protocol.

Each skill lives in its own directory under `skills/`:

```text
skills/
  my-skill/
    SKILL.md
```

The file contains YAML frontmatter followed by a Markdown body. Frontmatter is
used for discovery and capability/provider projection; the body is disclosed as
guidance when the skill is selected.

## Frontmatter

```yaml
---
name: warehouse-orders
display_name: Warehouse Orders
version: 0.1.0
description: >-
  Look up and create warehouse orders using the warehouse provider.
capabilities_required:
  - warehouse.orders.read
  - warehouse.orders.create.prepare
provider_ids:
  - warehouse
connection_id: warehouse
requires_verified_connection: true
fresh_source_capabilities:
  - warehouse.orders.read
triggers:
  - "order status"
  - "create order"
metadata:
  domain: orders
---
```

### `name`

Required, unique within the plugin. Use lowercase letters, numbers, and hyphens.

### `display_name`

Optional human-readable name for the admin UI.

### `version`

Optional semver-like skill content version. Bump it when the domain guidance
changes materially.

### `description`

Required short domain summary. Describe what the skill helps the Agent
understand or do; do not describe Host approval, persistence, receipts, or
internal action plumbing.

### `capabilities_required`

Capabilities whose knowledge/use this guidance depends on. This field does not grant a capability,
authorize an operation, execute a provider call, or create an approval requirement. A capability must still be declared, available,
authorized, and projected by the World/Host for the current turn.

For an `external_write` capability with a declared prepared-action contract,
the model-facing preparation capability is normally named with `.prepare`, for
example:

```yaml
capabilities_required:
  - warehouse.orders.read
  - warehouse.orders.create.prepare
```

### Provider metadata

Use `provider_ids` to identify provider guidance when a skill spans a known
provider. Use `connection_id` and `requires_verified_connection` for guidance
that only makes sense when one connection has been discovered and verified.
Use `fresh_source_capabilities` to identify read capabilities that should ground
current provider facts. These fields guide discovery; they do not grant access.

`metadata` is optional, non-authoritative domain metadata. Do not put secrets,
authority decisions, action identifiers, or runtime state in it.

### `triggers`

Optional natural-language phrases that help the router identify relevant
domain guidance. Keep them concise and include ordinary user vocabulary in the
languages used by the plugin.

## Effects in the plugin contract

The effect is declared by the capability in `plugin.json`, not by a skill:

| Effect | Meaning |
|---|---|
| `read` | Does not cause an external business mutation. |
| `write` | Local or internal mutation under Host authority. |
| `external_write` | External business effect governed by exact-effect Host authorization, declared idempotency, and declared completion evidence. |

An `external_write` capability does not necessarily require a second human
approval. The contract and current instruction determine the applicable path;
the skill should describe only the business domain.

## Where behavior belongs

### Manifest / Capability

Declare structural facts such as:

- effect;
- authority requirement and audience;
- inputs and outputs;
- resources and provider topology;
- `prepared_action` contract;
- idempotency contract;
- completion evidence.

Reviewable actions may additionally declare `prepare_capability` and
`execute_capability` in the manifest contract. These fields describe the
provider/SDK graph; they are not instructions to copy into a skill body.

### Skill

Teach domain meaning, for example:

- when to use a capability;
- business parameters and required facts;
- provider-specific semantics;
- business edge cases and reconciliation guidance;
- how to verify the resulting business state with a provider read.

### Host

The runtime owns exact effect binding, prepared-action persistence, the
authorization lifecycle, execution, idempotency enforcement, operations,
completion evidence, continuation, and reconciliation.

Skills guide reasoning about the domain. They do not reimplement or explain the
Host execution protocol.

## Body guidance

Write the body as concise instructions to the Agent. Include valid business
parameter values, provider-specific constraints, and safe edge-case handling.
Keep the body under roughly 400 lines.

Good domain guidance includes:

- required order fields and valid status values;
- how to distinguish a reply from a new message;
- how to identify an unambiguous shipment;
- which provider read verifies a saved product state.

Do not include runtime lifecycle instructions such as action storage,
authorization objects, continuation references, execution helper names, receipt
plumbing, or Host persistence mechanics. Removing that prose does not remove the
lifecycle from the Agent: the runtime projects it structurally through the
capability contract, World state, tool schemas, and structured results.

## Example skill

```yaml
---
name: warehouse-order-management
display_name: Warehouse Order Management
version: 0.1.0
description: >-
  Look up and create warehouse orders with warehouse-specific business rules.
capabilities_required:
  - warehouse.orders.read
  - warehouse.orders.create.prepare
provider_ids:
  - warehouse
triggers:
  - "order status"
  - "create warehouse order"
---
```

```markdown
# Warehouse Order Management

## When to use

Use the order capabilities for status lookups, new orders, and provider
reconciliation.

## Required data

For a new order, collect the customer reference, SKU, positive integer quantity,
and complete delivery address. Preserve the provider's currency and any
warehouse-specific shipping constraints.

## Business rules

Do not create an order for an unavailable SKU. If the provider reports an
ambiguous result or timeout, inspect the same order reference before trying
again. After creation, read the order back when the customer needs its current
status or identifier.
```

The example explains what data and domain rules matter. It does not mention
execution helpers, approval objects, or completion-evidence internals.
