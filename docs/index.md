# nutria-plugin SDK — Documentation

Developer reference for building, packaging, signing, and publishing Nutria plugins.

## Contents

| Document | What you'll find |
|----------|-----------------|
| [quickstart.md](quickstart.md) | Build and install your first plugin in 5 minutes |
| [manifest.md](manifest.md) | Complete `plugin.json` field reference |
| [admin-extensions.md](admin-extensions.md) | Declarative admin/frontend extensions for host-rendered plugin UI |
| [connection-types.md](connection-types.md) | All 4 runtime types with annotated examples |
| [skill-format.md](skill-format.md) | `SKILL.md` frontmatter schema and authoring guide |
| [security.md](security.md) | Signing, trust policies, ZIP safety rules, secrets |
| [cli.md](cli.md) | All `nutria-plugin` CLI commands and flags |
| [python-api.md](python-api.md) | Python API reference for programmatic usage |

## What is a Nutria plugin?

A Nutria plugin is a signed ZIP archive that grants a persona access to
external systems — REST APIs, SOAP services, MCP servers — without requiring
any new server deployment.

Plugins define:
- **Connections** — which external systems to call and how to authenticate
- **Skills** — instructions that tell the persona *when* and *how* to use those connections
- **Context docs** — reference material injected into the persona's prompt
- **Hooks** — event-driven actions (e.g. notify on shipment created)
- **Settings schema** — admin-configurable options shown in the Nutria UI
- **Admin extensions** — safe, declarative operator views rendered by the Nutria host

## Minimal plugin structure

```
my-plugin/
  plugin.json              # manifest (required)
  connections/
    my-api.json            # one file per connection
  skills/
    my-skill/
      SKILL.md             # one SKILL.md per skill
  context_docs/
    guide.md               # reference docs for the persona
  specs/                   # OpenAPI/WSDL specs (if applicable)
  hooks/hooks.json         # event hooks
  settings.schema.json     # admin settings schema
  assets/                  # optional icons
  README.md                # human-readable description
```

## Version

This documentation describes `nutria-plugin` **v0.0.1.5b0**.

API and file format compatibility are not yet guaranteed between pre-release releases.
