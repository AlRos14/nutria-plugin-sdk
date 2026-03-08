# Python API Reference

The `nutria_plugin` package exposes a public Python API for programmatic
plugin development, CI/CD integration, and runtime install logic.

## Import

```python
from nutria_plugin import (
    # Version
    __version__,
    # Manifest models
    PluginManifest,
    PluginPaths,
    PluginCompatibility,
    PluginScope,
    PluginRuntimeType,
    # Bundle operations
    PluginBundleError,
    load_plugin_bundle,
    extract_plugin_bundle,
    validate_zip,
    # Packaging
    PackagingError,
    scaffold_plugin,
    pack_plugin,
    validate_plugin_dir,
    # Signing
    SignatureStatus,
    generate_keypair,
    sign_manifest,
    verify_manifest,
)
```

---

## Manifest models

### `PluginManifest`

Pydantic v2 model representing the contents of `plugin.json`.

```python
from pathlib import Path
from nutria_plugin import PluginManifest

# Load from file
manifest = PluginManifest.from_file(Path("plugin.json"))

# Parse from raw bytes
manifest = PluginManifest.from_json_bytes(raw_bytes)

# Access fields
print(manifest.id)             # "my-plugin"
print(manifest.version)        # "0.1.0"
print(manifest.runtime_types)  # [PluginRuntimeType.DECLARATIVE_API]

# Write back to file
manifest.to_file(Path("plugin.json"))

# Serialize to dict
data = manifest.model_dump(mode="json", exclude_none=True)
```

**Class methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `from_file` | `(path: Path) -> PluginManifest` | Load from `plugin.json` on disk |
| `from_json_bytes` | `(raw: bytes) -> PluginManifest` | Parse from raw JSON bytes |

**Instance methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_file` | `(path: Path) -> None` | Write manifest to a file |
| `model_dump` | `(**kwargs) -> dict` | Pydantic serialization (supports `mode="json"`, `exclude_none=True`) |

---

### `PluginRuntimeType`

```python
from nutria_plugin import PluginRuntimeType

PluginRuntimeType.REMOTE_MCP       # "remote_mcp"
PluginRuntimeType.DECLARATIVE_API  # "declarative_api"
PluginRuntimeType.OPENAPI_BRIDGE   # "openapi_bridge"
PluginRuntimeType.SOAP_BRIDGE      # "soap_bridge"
```

---

### `PluginScope`

```python
from nutria_plugin import PluginScope

PluginScope.PLATFORM  # "platform"
PluginScope.STORE     # "store"
PluginScope.PERSONA   # "persona"
```

---

### `PluginCompatibility`

```python
from nutria_plugin import PluginCompatibility

compat = PluginCompatibility(
    min_nutria_version="0.10.0",
    max_nutria_version=None,
)
```

---

### `PluginPaths`

Override default file paths inside the plugin ZIP.

```python
from nutria_plugin import PluginPaths

paths = PluginPaths(
    connections_dir="connections",
    skills_dir="skills",
    context_docs_dir="context_docs",
    settings_schema="settings.schema.json",
    hooks_file="hooks/hooks.json",
    specs_dir="specs",
    assets_dir="assets",
)
```

---

## Bundle operations

### `load_plugin_bundle`

Parse and validate a plugin ZIP from bytes, returning the manifest.

```python
from nutria_plugin import load_plugin_bundle

zip_bytes = Path("my-plugin-0.1.0.zip").read_bytes()
manifest = load_plugin_bundle(zip_bytes)
print(manifest.id)
```

**Signature:** `load_plugin_bundle(data: bytes) -> PluginManifest`

**Raises:** `PluginBundleError` if the ZIP is malformed, unsafe, or the
manifest is invalid.

---

### `extract_plugin_bundle`

Extract a validated plugin ZIP to a target directory.

```python
from pathlib import Path
from nutria_plugin import extract_plugin_bundle

zip_bytes = Path("my-plugin-0.1.0.zip").read_bytes()
manifest = extract_plugin_bundle(zip_bytes, Path("/opt/nutria/plugins/my-plugin"))
```

**Signature:** `extract_plugin_bundle(data: bytes, target_dir: Path) -> PluginManifest`

**Raises:** `PluginBundleError` on any safety or manifest error.

---

### `validate_zip`

Validate a ZIP archive without extracting it. Returns a list of error
strings (empty list means valid).

```python
from nutria_plugin import validate_zip

errors = validate_zip(zip_bytes)
if errors:
    for e in errors:
        print(f"Error: {e}")
```

**Signature:** `validate_zip(data: bytes) -> list[str]`

---

### `PluginBundleError`

Exception raised by bundle operations.

```python
from nutria_plugin import PluginBundleError

try:
    manifest = load_plugin_bundle(zip_bytes)
except PluginBundleError as e:
    print(f"Bundle error: {e}")
```

---

## Packaging

### `scaffold_plugin`

Create a new plugin directory with the standard structure.

```python
from pathlib import Path
from nutria_plugin import scaffold_plugin

scaffold_plugin(
    plugin_id="my-plugin",
    name="My Plugin",
    target_dir=Path("my-plugin"),
)
```

**Signature:** `scaffold_plugin(plugin_id: str, name: str | None, target_dir: Path) -> None`

---

### `validate_plugin_dir`

Validate a plugin directory on disk. Returns a list of error strings.

```python
from pathlib import Path
from nutria_plugin import validate_plugin_dir

errors = validate_plugin_dir(Path("my-plugin"))
if not errors:
    print("Valid")
else:
    for e in errors:
        print(f"  - {e}")
```

**Signature:** `validate_plugin_dir(plugin_dir: Path) -> list[str]`

**Notes:**
- Hidden files (`.gitignore`, `.DS_Store`) are silently skipped.
- Symlinks in the directory are reported as errors.

---

### `pack_plugin`

Validate and pack a plugin directory into a ZIP archive.

```python
from pathlib import Path
from nutria_plugin import pack_plugin

out_path = pack_plugin(
    plugin_dir=Path("my-plugin"),
    output_path=Path("dist/my-plugin-0.1.0.zip"),
    sign=True,
    private_key_pem=Path("my-signing-key.pem").read_text(),
)
print(f"Packed: {out_path}")
```

**Signature:**
```python
pack_plugin(
    plugin_dir: Path,
    output_path: Path | None = None,
    sign: bool = False,
    private_key_pem: str | None = None,
) -> Path
```

| Parameter | Description |
|-----------|-------------|
| `plugin_dir` | Source plugin directory |
| `output_path` | Output ZIP path. Defaults to `<id>-<version>.zip` in CWD |
| `sign` | If `True`, sign the manifest before packing |
| `private_key_pem` | PEM private key string (required if `sign=True`) |

**Raises:** `PackagingError` on validation failure or I/O error.

---

### `PackagingError`

Exception raised by packaging operations.

```python
from nutria_plugin import PackagingError

try:
    pack_plugin(Path("my-plugin"))
except PackagingError as e:
    print(f"Packaging failed: {e}")
```

---

## Signing

### `generate_keypair`

Generate an ECDSA P-256 key pair.

```python
from nutria_plugin import generate_keypair

private_pem, public_pem = generate_keypair()
# private_pem: str — PEM-encoded private key
# public_pem:  str — PEM-encoded public key
```

**Signature:** `generate_keypair() -> tuple[str, str]`

---

### `sign_manifest`

Sign a manifest dict and return the hex-encoded DER signature.

```python
from nutria_plugin import sign_manifest

manifest_dict = {"id": "my-plugin", "version": "0.1.0", ...}
signature_hex = sign_manifest(manifest_dict, private_key_pem)

# The signature is stored in plugin.json under the "signature" key
manifest_dict["signature"] = signature_hex
```

**Signature:** `sign_manifest(manifest: dict, private_key_pem: str) -> str`

The signing payload is the canonical JSON serialization of `manifest` with
the `"signature"` field removed.

---

### `verify_manifest`

Verify the signature in a manifest dict against the trusted public keys
configured via `NUTRIA_PLUGIN_TRUSTED_KEYS`.

```python
from nutria_plugin import verify_manifest, SignatureStatus

status = verify_manifest(manifest_dict)

if status == SignatureStatus.VERIFIED:
    print("Signature valid and trusted")
elif status == SignatureStatus.UNSIGNED:
    print("No signature present")
elif status == SignatureStatus.INVALID:
    print("Signature present but verification failed")
elif status == SignatureStatus.UNTRUSTED:
    print("Signature valid but key not in trusted list")
elif status == SignatureStatus.MISSING:
    print("No trusted keys configured — cannot verify")
```

**Signature:** `verify_manifest(manifest: dict) -> SignatureStatus`

**Environment variable:** `NUTRIA_PLUGIN_TRUSTED_KEYS` — JSON array of
PEM public key strings.

---

### `SignatureStatus`

Enum returned by `verify_manifest`.

| Value | Meaning |
|-------|---------|
| `SignatureStatus.VERIFIED` | Signature valid and key is trusted |
| `SignatureStatus.UNSIGNED` | No `signature` field in manifest |
| `SignatureStatus.INVALID` | Signature present but cryptographic verification failed |
| `SignatureStatus.UNTRUSTED` | Signature cryptographically valid but key not in trusted list |
| `SignatureStatus.MISSING` | `NUTRIA_PLUGIN_TRUSTED_KEYS` not configured |

---

## CI/CD integration example

```python
from pathlib import Path
from nutria_plugin import validate_plugin_dir, pack_plugin

def ci_build(plugin_dir: Path, signing_key: str, output_dir: Path) -> None:
    errors = validate_plugin_dir(plugin_dir)
    if errors:
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)

    out = pack_plugin(
        plugin_dir=plugin_dir,
        output_path=output_dir / "release.zip",
        sign=True,
        private_key_pem=signing_key,
    )
    print(f"Built: {out}")
```
