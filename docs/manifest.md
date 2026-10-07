# plugin.json manifest reference

`plugin.json` is the single source of truth for plugin identity, runtime,
capability authority, and provider topology. SDK 0.6.0 accepts exactly schema
`5.0`; older schemas and unknown fields fail validation.

## Required top-level fields

| Field | Contract |
|---|---|
| `schema_version` | Literal `"6.0"` |
| `id` | Lowercase plugin slug |
| `name`, `description`, `author` | Non-empty display metadata |
| `version` | Semantic version |
| `runtime_types` | One or more supported runtime types |
| `capabilities` | At least one typed capability |
| `world_providers` | At least one typed provider |

Optional fields include `default_scope`, `paths`, `required_secrets`,
`optional_secrets`, `remote_endpoints`, `tags`, `reviewable_actions`,
`admin_extensions`, `admin_flows`, `mcp_server_entry`, `homepage`, `license`,
and `signature`. A `compatibility` field is not part of schema 6.0.

## Capability descriptor

Each capability declares:

- stable `id`, `title`, and `description`;
- `effect`: `read`, `write`, or `external_write` (the authority/mutation dimension);
- `effect_scope`: `agent_local`, `internal_state`, `lifecycle`, or `world` (where the effect lands);
- concrete `tool` and optional `connection_id`;
- typed `inputs`, `consumes`, and `produces` bindings, each carrying a `data_class`;
- required `requirements.authority` and `requirements.audience`, plus resolved
  `requirements.task_context` (`required`, `optional`, or `forbidden`, default
  `optional`);
- required `exposure`: `model`, `host`, or `admin`;
- for every non-read capability, an explicit `completion` contract.

`host` and `admin` exposure require `non_callable_reason` with a stable code and
safe summary. `model` exposure must not declare it. Hosts structurally promote
task-owned resource bindings to effective `task_context: "required"`.

### Effect and effect scope

`effect` says how much authority a call needs. `effect_scope` is orthogonal and says
where the effect lands:

| `effect_scope` | Examples |
|---|---|
| `agent_local` | terminal, scratch files |
| `internal_state` | notebook, memory, preferences |
| `lifecycle` | Interactions, Tasks, PreparedAction storage |
| `world` | WooCommerce, MRW, Trello, email, WhatsApp |

`effect_scope: world` does **not** mean only world effects can complete an Objective.
"Remember this" legitimately completes through `internal_state`. A completion
expectation never exists merely because `effect != read`: it exists only when the
capability declares completion evidence.

### Completion contract

Every non-read capability declares exactly one of:

```json
"completion": {"evidence": "none"}
```

or

```json
"completion": {
  "evidence": "declared",
  "receipts": ["email.sent"],
  "basis": "delivery_confirmation",
  "targets": "single"
}
```

`basis` is one of `provider_outcome`, `confirmed_mutation`, `verified_readback`,
`delivery_confirmation` (two-phase: acceptance is not delivery), or `prepared_action`.
`targets: all_requested` means a multi-target effect is complete only when every
requested target is confirmed; a partial result stays `partial`. Read capabilities must
not declare completion. Hosts never synthesize receipts for writes.

Handlers report facts under `operation_facts` (see `OperationFacts`); they do not conclude
`completed`. `validate_capability_result` checks that reported facts can satisfy the
declared contract (declared receipts present on a confirmed mutation, basis respected,
no receipts when evidence is `none`).

### Data classification

Every input and output binding declares `data_class`:

| `data_class` | Meaning |
|---|---|
| `non_personal` | public or non-personal content |
| `business_resource_identifier` | product, order, SKU, EAN style identifiers |
| `operational_identifier` | internal operational refs (tracking, ids with no person) |
| `personal_identifier` | name, phone, email, address of a person |
| `personal_content` | free text that may contain personal data |
| `special_category` | health, biometric, and other special categories |

The contract declares the class; hosts must not infer it from field names. `semantic_field`
continues to carry semantic identity. `requires_provenance` stays independent.

### Validation rules enforced by the SDK

| Rule | Error contains |
|---|---|
| non-read capability without `completion` | `must declare completion explicitly` |
| read capability with `completion` | `must not declare completion` |
| `external_write` outside `effect_scope: world` | `effect_scope 'world'` |
| `agent_local` with declared completion evidence | `agent_local` |
| model-exposed `external_write` without `prepared_action` | `require prepared_action` |
| model-exposed world write without declared evidence | `declared completion evidence` |
| model-exposed world write without required idempotency | `execution idempotency` |
| `declared` evidence without receipts or basis | `requires receipts` / `requires a basis` |
| input/output without `data_class`, or legacy `sensitivity` | `data_class` / `sensitivity` |
| skill frontmatter with `triggers` (or any unknown key) | `triggers` |
| reviewable action referencing unknown or mis-typed capabilities | existing reviewable errors |

Model-exposed `external_write` capabilities also declare `prepared_action`,
`idempotency` and `completion`. Reviewable delivery capabilities are instead
host-only and are linked through `reviewable_action_id`.

## World provider descriptor

Every provider declares a stable ID, title, description, optional connection
and health capability, and one or more resource types. Each resource type has:

- a stable built-in or plugin-namespaced `id`;
- one or more `identity_fields`;
- optional search/inspect capability references;
- optional version field, TTL, and named safe/authorized projections.

Capability connections must have a matching provider connection. Referenced
search, inspect, health, prepare, and execute capabilities must exist in the
same manifest.

## Reviewable actions

The host owns the encrypted draft and approval lifecycle. A reviewable action
maps stable semantic fields to one host-only external-write capability. Every
delivery maps `recipient`, `body`, and `idempotency_key`; required capability
inputs must be mapped. Preparation capabilities produce `prepared_action` and
declare their actual `read` or `write` mutation scope. See
[reviewable-actions.md](reviewable-actions.md).

## Paths and settings

All component paths are relative and cannot contain empty, `.` or `..`
segments. `settings.schema.json` may use the host extensions
`x-nutria-store-scoped` and `x-nutria-store-default-key` for values that truly
vary by store.

## Secrets and endpoints

Secret arrays contain names only. Remote endpoints must be absolute HTTP(S)
URLs and cannot target localhost, loopback, link-local, private, or reserved IP
ranges.

## Validation

```bash
uv run nutria-plugin validate .
uv run nutria-plugin pack . --output dist/plugin.zip
```
