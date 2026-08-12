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

__version__ = "0.2.2"

from .capabilities import (
    CapabilityDescriptor,
    CapabilityEffect,
    CapabilityExposure,
    CapabilityInputBinding,
    CapabilityOutputBinding,
    CapabilityRequirement,
    CompletionDescriptor,
    IdempotencyDescriptor,
    NonCallableReason,
    PreparedActionDescriptor,
    ResourceBinding,
    ResourceType,
    ResourceTypeDescriptor,
    WorldProjectionDescriptor,
    WorldProviderDescriptor,
)


from .manifest import (
    PluginAdminExtension,
    PluginAdminExtensionKind,
    PluginAdminExtensionPlacement,
    PluginAdminFlow,
    PluginAdminFlowKind,
    PluginAdminFlowPlacement,
    PluginCompatibility,
    PluginManifest,
    PluginPaths,
    PreparationToolContract,
    ReviewableActionContract,
    ReviewableActionField,
    ReviewableActionMode,
    PluginRuntimeType,
    PluginScope,
)
from .bundle import PluginBundleError, extract_plugin_bundle, load_plugin_bundle, validate_zip
from .packaging import PackagingError, pack_plugin, scaffold_plugin, validate_plugin_dir
from .signing import SignatureStatus, generate_keypair, sign_manifest, verify_manifest

__all__ = [
    "__version__",
    # Manifest
    "PluginManifest",
    "PluginPaths",
    "PluginCompatibility",
    "PluginScope",
    "PluginRuntimeType",
    "PluginAdminExtension",
    "PluginAdminExtensionKind",
    "PluginAdminExtensionPlacement",
    "PluginAdminFlow",
    "PluginAdminFlowKind",
    "PluginAdminFlowPlacement",
    "ReviewableActionContract",
    "ReviewableActionMode",
    "ReviewableActionField",
    "PreparationToolContract",
    "CapabilityDescriptor",
    "CapabilityEffect",
    "CapabilityExposure",
    "CapabilityInputBinding",
    "CapabilityOutputBinding",
    "CapabilityRequirement",
    "CompletionDescriptor",
    "IdempotencyDescriptor",
    "NonCallableReason",
    "PreparedActionDescriptor",
    "ResourceBinding",
    "ResourceType",
    "ResourceTypeDescriptor",
    "WorldProjectionDescriptor",
    "WorldProviderDescriptor",
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
