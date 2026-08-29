# nutria-plugin SDK documentation

Developer reference for SDK `0.4.2` and manifest schema `4.0`.

| Document | Purpose |
|---|---|
| [quickstart.md](quickstart.md) | Build a strict schema 4.0 plugin |
| [manifest.md](manifest.md) | Manifest, capability, and provider contracts |
| [reviewable-actions.md](reviewable-actions.md) | Host-owned drafts and external delivery |
| [python-api.md](python-api.md) | Public Python API |
| [connection-types.md](connection-types.md) | Supported runtime/connection types |
| [skill-format.md](skill-format.md) | Skill frontmatter and authoring |
| [admin-extensions.md](admin-extensions.md) | Host-rendered admin views |
| [admin-flows.md](admin-flows.md) | Host-rendered operator flows |
| [security.md](security.md) | Signing, ZIP safety, endpoints, and secrets |
| [cli.md](cli.md) | CLI commands |

A plugin bundle can contain connections, skills, context documents, hooks,
settings, specs, and declarative admin assets. Its schema 4.0 manifest must also
declare at least one typed capability and world provider. Older schemas are not
loaded or migrated.
