# plugin.json manifest reference

`plugin.json` is the single source of truth for plugin identity, runtime,
capability authority, and provider topology. SDK 0.4.0 accepts exactly schema
`4.0`; older schemas and unknown fields fail validation.

## Required top-level fields

| Field | Contract |
|---|---|
| `schema_version` | Literal `"4.0"` |
| `id` | Lowercase plugin slug |
| `name`, `description`, `author` | Non-empty display metadata |
| `version` | Semantic version |
| `runtime_types` | One or more supported runtime types |
| `capabilities` | At least one typed capability |
| `world_providers` | At least one typed provider |

Optional fields include `default_scope`, `paths`, `required_secrets`,
`optional_secrets`, `remote_endpoints`, `tags`, `reviewable_actions`,
`admin_extensions`, `admin_flows`, `mcp_server_entry`, `homepage`, `license`,
and `signature`. A `compatibility` field is not part of schema 4.0.

## Capability descriptor

Each capability declares:

- stable `id`, `title`, and `description`;
- `effect`: `read`, `write`, or `external_write`;
- concrete `tool` and optional `connection_id`;
- typed `inputs`, `consumes`, and `produces` bindings;
- required `requirements.authority` and `requirements.audience`, plus resolved
  `requirements.task_context` (`required`, `optional`, or `forbidden`, default
  `optional`);
- required `exposure`: `model`, `host`, or `admin`.

`host` and `admin` exposure require `non_callable_reason` with a stable code and
safe summary. `model` exposure must not declare it. Hosts structurally promote
task-owned resource bindings to effective `task_context: "required"`.

A model-exposed `external_write` must declare `prepared_action`, `idempotency`,
and `completion`. Reviewable delivery capabilities are instead host-only and
are linked through `reviewable_action_id`.

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
