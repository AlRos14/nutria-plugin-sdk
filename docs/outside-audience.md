# Capabilities for an outside audience

An agent that answers a person outside the company works in a `public_customer` turn. A capability is offered to that
audience only if its manifest says so (`requirements.audience` contains `public_customer`). Most capabilities are not.

## The rule

A capability offered to `public_customer`:

- is a **read** (`effect: read`); writes and sends go through the host's own approval path;
- takes **no person-identifying input** (`data_class: personal_identifier`) except the one scoped to the conversation contact;
- if it returns `personal_content` or `special_category` data, **must scope an input to the conversation contact**.

## Scoping an input

```json
{"kind": "value", "semantic_field": "chat", "argument_name": "chat", "required": false,
 "data_class": "personal_identifier", "accepted_origins": ["current_user"], "scope": "conversation_contact"}
```

`scope: "conversation_contact"` means: this argument names the one person the conversation is with. In an outside-audience
turn the host **sets it itself**, replacing whatever the model sent and filling it when the model left it out. The person
writing to the agent cannot choose another chat by mentioning it. Only a `value` input of class `personal_identifier` can carry
the scope, and a capability has at most one.

`nutria_plugin.apply_conversation_scope(capability, arguments, contact)` is the reference rule hosts and plugin tests share.

## What the plugin must guarantee

The host fixes the argument; the plugin must make sure that, when the argument is given, **every** result belongs to that
person: a search with a chat never returns another chat, an item fetched by id is refused when it is not part of that chat,
and a list is limited to that chat. A capability that cannot guarantee this must not declare `public_customer`.

## What is not covered

A capability that needs no contact (for example public pickup points) declares `public_customer` without a scope. It must not
return personal content. A resource a person quotes (such as a tracking number) is not a conversation scope: decide whether the
data behind it is safe to show to whoever sends that number.
