"""nutria_plugin — Nutria Plugin SDK

Public API
----------
Models:
    PluginManifest, PluginPaths, PluginCompatibility, PluginScope, PluginRuntimeType

Bundle operations:
    load_plugin_bundle, extract_plugin_bundle, validate_zip

Packaging:
    scaffold_plugin, pack_plugin, validate_plugin_dir, PackagingError

Signing:
    generate_keypair, sign_manifest, verify_manifest, SignatureStatus
"""

from .bundle import PluginBundleError, extract_plugin_bundle, load_plugin_bundle, validate_zip
from .manifest import (
    PluginCompatibility,
    PluginManifest,
    PluginPaths,
    PluginRuntimeType,
    PluginScope,
)
from .packaging import PackagingError, pack_plugin, scaffold_plugin, validate_plugin_dir
from .signing import SignatureStatus, generate_keypair, sign_manifest, verify_manifest

__all__ = [
    # Manifest
    "PluginManifest",
    "PluginPaths",
    "PluginCompatibility",
    "PluginScope",
    "PluginRuntimeType",
    # Bundle
    "PluginBundleError",
    "load_plugin_bundle",
    "extract_plugin_bundle",
    "validate_zip",
    # Packaging
    "PackagingError",
    "scaffold_plugin",
    "pack_plugin",
    "validate_plugin_dir",
    # Signing
    "SignatureStatus",
    "generate_keypair",
    "sign_manifest",
    "verify_manifest",
]
