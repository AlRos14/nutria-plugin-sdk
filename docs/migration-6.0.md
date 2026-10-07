# Migrating a plugin from schema 5.0 to 6.0

Schema 6.0 is a breaking release (SDK 0.6.0). 5.0 manifests fail validation.

## What changed

| 5.0 | 6.0 |
|---|---|
| `completion: {"receipts": [...]}` optional, synthesized for writes by the host | `completion` required on every non-read capability: `{"evidence": "none"}` or `{"evidence": "declared", receipts, basis, targets}` |
| no effect scope | `effect_scope` required: `agent_local`, `internal_state`, `lifecycle`, `world` |
| input `sensitivity: safe | personal` | input and output `data_class` (six classes) |
| skill `triggers` tolerated by docs | rejected |
| handler results ad hoc | `operation_facts` (`OperationFacts`) |

## Steps

1. `uv add nutria-plugin==0.6.0`
2. `uv run nutria-plugin migrate plugin.json` applies the mechanical changes, removes the
   `signature`, and prints `REVIEW:` lines for every judgement call.
3. Review each item. The tool picks conservative values:
   - `effect_scope`: external writes become `world`; other writes are guessed from
     `connection_id` and must be confirmed.
   - `completion.basis` defaults to `provider_outcome`: choose `confirmed_mutation`,
     `verified_readback`, `delivery_confirmation` (two-phase delivery) or `prepared_action`.
   - `personal` inputs become `personal_identifier`; use `personal_content` for free text
     and `special_category` where it applies. Identifiers that are not personal
     (SKU, EAN, product id, tracking number) are `business_resource_identifier` or
     `operational_identifier`.
4. Remove `triggers` from every `SKILL.md`.
5. Make handlers report `operation_facts` and cover them with
   `validate_capability_result` in the plugin test-suite.
6. `uv run nutria-plugin validate .`, then re-sign.
