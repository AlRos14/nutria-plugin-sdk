# Reviewable actions and capability contracts

`nutria-plugin` 0.2.0 defines the contract between ChatBotNutralia and a
delivery plugin. There is one draft system:

```text
ChatBotNutralia  ->  identity, draft, revisions, approval, continuity, receipts
Plugin            ->  channel reads, pure preparation, exact delivery, audit
SDK               ->  typed capability and reviewable-action contract
```

Plugins do not save drafts and do not expose native `send_saved_*` operations.
The host invokes a delivery capability only after a human approves the exact
encrypted snapshot stored in `PreparedToolAction`.

## Manifest version 2.0

Every plugin manifest must declare `"schema_version": "2.0"`. The manifest
contains typed capabilities and, when applicable, reviewable actions:

```json
{
  "schema_version": "2.0",
  "id": "whatsapp-wacli",
  "name": "WhatsApp WACLI",
  "version": "1.0.0",
  "description": "WhatsApp reads and exact approved delivery.",
  "author": "Nutria",
  "runtime_types": ["remote_mcp"],
  "capabilities": [
    {
      "id": "whatsapp.send.text",
      "title": "Send WhatsApp text",
      "description": "Deliver the approved message without rewriting it.",
      "effect": "external_write",
      "tool": "send_whatsapp_text",
      "connection_id": "nutria-whatsapp-wacli--wacli",
      "model_callable": false,
      "reviewable_action_id": "whatsapp-text",
      "inputs": [
        {"semantic_field": "recipient", "argument_name": "recipient"},
        {"semantic_field": "body", "argument_name": "body"},
        {"semantic_field": "reply_target", "argument_name": "reply_to_message_id", "required": false},
        {"semantic_field": "audit_context", "argument_name": "audit_context_json", "required": false},
        {"semantic_field": "idempotency_key", "argument_name": "idempotency_key"}
      ],
      "produces": [
        {"field_name": "operation_ref", "output_name": "operation", "resource_type": "operation"}
      ]
    }
  ],
  "reviewable_actions": [
    {
      "id": "whatsapp-text",
      "kind": "customer_message",
      "channel": "whatsapp",
      "modes": ["new", "reply"],
      "connection_id": "nutria-whatsapp-wacli--wacli",
      "execute_capability": "whatsapp.send.text",
      "argument_map": {
        "recipient": "recipient",
        "body": "body",
        "reply_target": "reply_to_message_id",
        "audit_context": "audit_context_json",
        "idempotency_key": "idempotency_key"
      },
      "required_fields": ["recipient", "body"],
      "editable_fields": ["body"]
    }
  ]
}
```

## Capability fields

`CapabilityDescriptor` is the typed resource graph edge for one tool.

- `id` is the stable capability identity used by the host.
- `effect` is `read`, `prepare`, `write`, or `external_write`.
- `tool` is the concrete connection tool name.
- `connection_id` and `requirements` identify the runtime dependency.
- `inputs` map semantic fields to tool arguments and may declare a resource type.
- `consumes` and `produces` describe graph resources, not raw PII.
- `model_callable=false` hides host-only delivery from the model.
- `reviewable_action_id` links an external write to its host contract.

The host rejects duplicate IDs, unknown references, unsafe names, inconsistent
connections, duplicate semantic arguments, and a reviewable external write
that is callable by the model.

## Reviewable action fields

`ReviewableActionContract` selects a channel and one or more modes (`new` or
`reply`). Its `argument_map` maps the stable semantic vocabulary: `recipient`,
`body`, `subject`, `html_body`, `reply_target`, `source_ref`,
`source_fingerprint`, `order_id`, `audit_context`, `idempotency_key`,
`thread_id`, `channel`, and `mode`.

`recipient`, `source_ref`, `source_fingerprint`, `reply_target`, `order_id`,
`channel`, and `mode` are immutable. Only fields listed in `editable_fields` may
be patched. Required fields must be mapped, and every delivery contract must
map `idempotency_key` so the host can pass the immutable action ID.

## Pure reply preparation

A reply may declare a preparation capability with `effect: "prepare"`:

```json
{
  "id": "email.reply.prepare",
  "title": "Resolve email reply envelope",
  "description": "Read the source email and return thread metadata.",
  "effect": "prepare",
  "tool": "prepare_email_reply",
  "connection_id": "email",
  "model_callable": false
}
```

It may read the source email and return recipient, subject, thread headers, and
a source fingerprint. It must not persist a draft, mutate the provider, or
send. The execution capability receives the host's reviewed body and resolved
envelope; it must not regenerate reviewed content.

## Host workflow and offline behavior

The host exposes `prepare_customer_message`, `inspect_customer_message`,
`revise_customer_message`, and `send_customer_message`. A visible draft is
always rendered from the encrypted host snapshot and has a host action ID.
Each revision creates a new action ID and requires approval again. A plugin
being unavailable sets `delivery_ready=false` but does not remove the local
draft. Recovery revalidates the contract and source fingerprint; any changed
envelope creates a new revision.

Receipts use generic names (`reviewable_action.prepared`, `.read`, `.revised`,
`.sent`) and contain IDs, status, revision, verified field names, and
fingerprints only. Raw message bodies and recipient PII never appear in active
task metadata or logs.

## Validation and packaging

```bash
uv sync --dev
uv run nutria-plugin validate .
uv run nutria-plugin pack . --output dist/my-plugin-1.0.0.zip
uv run pytest
```

`validate_zip` applies the same manifest, capability, and ZIP path-security
checks used by the host installer.
