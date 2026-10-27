# Conversation ownership

A conversation with an outside person has one owner at a time. A channel plugin reports it in every inbound event; the host
decides which agent answers. The words are defined once, in `nutria_plugin.ownership`.

| Owner kind | Meaning | Answers |
| --- | --- | --- |
| `human` | A team member took the conversation | Nobody else. Agents may draft and open cases. |
| `agent` | An agent started it or was handed it (`owner_ref` is the agent id) | That agent, with its own identity and rules |
| `customer_service` | Nobody above owns it (the default) | The customer-service agent |

A weaker owner never takes a conversation from a stronger one. `locked: true` (set by a person) holds it against every agent,
including the owning one.

## In the event payload
```json
{"conversation_ownership": {"owner_kind": "human", "owner_ref": "alejandro", "locked": false, "reason": "manual_takeover"}}
```
A plugin that knows only who is a human (as the WhatsApp plugin did with `ownership_state`, `human_owned`, `reply_blocked`) keeps working:
`ownership_from_event_payload` maps those keys to the same model. A plugin that does not send ownership leaves the choice to the host.

## What a plugin must do
- Report the human state it can observe (a person answered from the phone or the web client, a manual lock) as `owner_kind: human`.
- Never decide which agent answers; that is the host's job (it also records agent ownership from its own deliveries).
- Refuse to deliver an agent message to a conversation the plugin knows is human-owned and locked.

## What a host must do
Resolve the answering agent from the plugin's report and its own ownership record, with the priority above; release agent ownership when the agent closes the
conversation, the contact asks to stop, a person takes over, or the conversation has been idle for the host's configured time.
