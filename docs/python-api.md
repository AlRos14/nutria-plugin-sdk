# Python API reference

SDK 0.3.0 exposes the strict schema 3.0 API.

```python
from nutria_plugin import (
    __version__,
    PluginManifest, PluginPaths, PluginScope, PluginRuntimeType,
    CapabilityDescriptor, CapabilityEffect, CapabilityExposure,
    CapabilityRequirement, CapabilityInputBinding, CapabilityOutputBinding,
    ResourceBinding, ResourceType, ResourceTypeDescriptor,
    WorldProjectionDescriptor, WorldProviderDescriptor,
    PreparedActionDescriptor, IdempotencyDescriptor, CompletionDescriptor,
    NonCallableReason,
    ReviewableActionContract, ReviewableActionField, ReviewableActionMode,
    PreparationToolContract,
    PluginAdminExtension, PluginAdminExtensionKind,
    PluginAdminExtensionPlacement,
    PluginAdminFlow, PluginAdminFlowKind, PluginAdminFlowPlacement,
    PluginBundleError, load_plugin_bundle, extract_plugin_bundle, validate_zip,
    PackagingError, scaffold_plugin, pack_plugin, validate_plugin_dir,
    SignatureStatus, generate_keypair, sign_manifest, verify_manifest,
)
```

`PluginCompatibility` and `model_callable` are not part of this API.
Callability is represented by `CapabilityExposure`; host/admin exposure also
requires `NonCallableReason`.

## Manifest

```python
from pathlib import Path
from nutria_plugin import PluginManifest

manifest = PluginManifest.from_file(Path("plugin.json"))
same = PluginManifest.from_json_bytes(Path("plugin.json").read_bytes())
manifest.to_file(Path("plugin.json"))
payload = manifest.model_dump(mode="json", exclude_none=True)
```

Validation is strict: schema version must be `3.0`, top-level extras are
rejected, and capability/provider/action references are checked together.

## Bundles and packaging

```python
from pathlib import Path
from nutria_plugin import (
    load_plugin_bundle, extract_plugin_bundle, validate_zip,
    scaffold_plugin, validate_plugin_dir, pack_plugin,
)

raw = Path("plugin.zip").read_bytes()
manifest = load_plugin_bundle(raw)
warnings = validate_zip(raw)
extract_plugin_bundle(raw, Path("installed/plugin"))

scaffold_plugin("my-plugin", "My Plugin", Path("."))
errors = validate_plugin_dir(Path("my-plugin"))
archive = pack_plugin(Path("my-plugin"), Path("dist/my-plugin.zip"))
```

Unsafe bundles raise `PluginBundleError`; invalid source directories or pack
operations raise `PackagingError`.

## Signing

```python
from nutria_plugin import generate_keypair, sign_manifest, verify_manifest

private_pem, public_pem = generate_keypair()
payload = manifest.model_dump(mode="json", exclude_none=True)
payload["signature"] = sign_manifest(payload, private_pem)
status = verify_manifest(payload)
```

Signing uses ECDSA P-256 over canonical JSON with the `signature` field removed.
