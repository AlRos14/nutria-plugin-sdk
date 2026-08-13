# Reviewable actions and external writes

SDK 0.3.0 schema 3.0 defines one reviewable-action architecture:

```text
ChatBotNutralia -> task context, encrypted draft, revision, approval, idempotency, receipts
Plugin           -> provider reads, pure preparation, exact approved delivery
SDK              -> strict capability/provider/reviewable-action contracts
```

Plugins do not save drafts and do not expose native saved-draft operations.

## Delivery capability

A reviewable delivery capability uses `effect: "external_write"`,
`exposure: "host"`, a `non_callable_reason`, explicit authority/audience/task
requirements, input bindings, and `reviewable_action_id`:

```json
{
  "id": "whatsapp.send.text",
  "title": "Send WhatsApp text",
  "description": "Deliver the exact approved message.",
  "effect": "external_write",
  "tool": "send_whatsapp_text",
  "connection_id": "whatsapp",
  "requirements": {
    "authority": "write_external",
    "audience": ["team_internal", "private_internal"],
    "task_context": "required"
  },
  "exposure": "host",
  "non_callable_reason": {
    "code": "host_approval_boundary",
    "safe_summary": "Executed only by the host after exact-snapshot approval."
  },
  "reviewable_action_id": "whatsapp-text",
  "inputs": [
    {"kind": "value", "semantic_field": "recipient", "argument_name": "recipient", "sensitivity": "personal", "accepted_origins": ["current_user", "world_resource"]},
    {"kind": "value", "semantic_field": "body", "argument_name": "body", "sensitivity": "personal", "accepted_origins": ["current_user"]},
    {"kind": "value", "semantic_field": "idempotency_key", "argument_name": "idempotency_key", "sensitivity": "safe", "accepted_origins": ["current_user"]}
  ]
}
```

The matching top-level action maps stable semantic fields to those exact tool
arguments:

```json
{
  "id": "whatsapp-text",
  "kind": "customer_message",
  "channel": "whatsapp",
  "modes": ["new", "reply"],
  "connection_id": "whatsapp",
  "execute_capability": "whatsapp.send.text",
  "argument_map": {
    "recipient": "recipient",
    "body": "body",
    "idempotency_key": "idempotency_key"
  },
  "required_fields": ["recipient", "body"],
  "editable_fields": ["body"]
}
```

Every delivery maps `idempotency_key`. Required execution inputs must appear in
the action map. Recipient, source/thread/order identities, channel, and mode are
immutable; only explicitly editable fields can change.

## Pure preparation

An optional reply-envelope preparation capability uses `effect: "prepare"`.
It may resolve authoritative recipient/thread/source fingerprints but cannot
persist a draft or write externally. The action's `prepare_capability` and
`execute_capability` must be distinct and use the same connection.

## Host lifecycle

The host exposes generic prepare, inspect, revise, and send operations. A
revision creates a new action identity and approval. Delivery executes the
approved body and immutable envelope exactly once. Success requires the
declared authoritative completion receipt; unavailable providers keep the local
draft but cannot produce a successful effect.

Validate the whole cross-reference graph with:

```bash
uv run nutria-plugin validate .
```
