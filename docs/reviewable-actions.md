# Reviewable actions

Reviewable actions establish one boundary between a host and a delivery-only
plugin:

```text
ChatBotNutralia: draft, revisions, approval, continuity, encrypted snapshot
Plugin:         channel reads, optional pure resolution, exact delivery, audit
SDK:            typed contract and validation
```

## Contract schema

Add `schema_version: "1.1"` and one or more contracts to `plugin.json`:

```json
{
  "id": "whatsapp-text",
  "kind": "customer_message",
  "channel": "whatsapp",
  "modes": ["new", "reply"],
  "connection_id": "nutria-whatsapp-wacli--wacli",
  "execute_tool": "send_whatsapp_text",
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
```

`modes` is a list of `new` and/or `reply`. Semantic fields are selected from
the SDK vocabulary (`recipient`, `body`, `subject`, `html_body`,
`reply_target`, `source_ref`, `source_fingerprint`, `order_id`,
`audit_context`, `idempotency_key`, `thread_id`, `channel`, and `mode`).
Required and editable fields must be mapped. Recipient, source identity, reply
target, channel, and mode are immutable by default; editable fields must not
overlap immutable fields. Every delivery contract must map `idempotency_key`
so the host can pass the immutable action ID and make retries safe.

## Optional preparation adapters

Reply contracts may declare a pure adapter:

```json
"prepare_tool": {
  "name": "prepare_email_reply",
  "external_write": false,
  "side_effect": "read"
}
```

The host may call it after a verified source read to resolve the current
recipient, subject, thread headers, and source fingerprint. It may not save a
draft, mutate external state, or send anything. The final execution tool must
send the host's exact reviewed payload; it must not regenerate the body.

## Validation and packaging

The SDK rejects duplicate contract IDs, unknown modes/semantic fields, unsafe
connection/tool names or argument mappings, missing recipient/body/idempotency
mappings, editable/immutable overlap, and preparation tools declared as
external writes.
Use the same commands in CI and before installation:

```bash
uv sync --dev
uv run nutria-plugin validate .
uv run nutria-plugin pack . --output dist/my-plugin-0.1.0.zip
uv run pytest
```

`validate_zip` applies the same manifest and ZIP path-security checks used by
the host installer.

## Offline behavior

If a plugin is installed but unhealthy, the host still prepares, inspects, and
revises the encrypted action. It reports `delivery_ready: false` and does not
send. Once the connector recovers, the host revalidates the contract. A changed
delivery envelope or source fingerprint blocks the send and requires a new host
revision and approval; the reviewed snapshot is never silently altered.
