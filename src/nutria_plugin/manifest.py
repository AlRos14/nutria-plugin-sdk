"""
Plugin manifest models for Nutria plugins.

These models are the canonical schema for plugin.json and are shared between
the SDK (for plugin authors) and the ChatBotNutralia runtime (for validation
at install time).
"""

from __future__ import annotations

import json
import hashlib
import re
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .capabilities import CapabilityDescriptor, CapabilityEffect

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


def _enum_value(value: Any) -> str:
    """Normalize enum members and JSON strings for cross-version Pydantic output."""
    return str(value.value if isinstance(value, Enum) else value)


def _validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ValueError("plugin component paths must be relative")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("plugin component paths cannot contain empty, '.' or '..' segments")
    return path.as_posix()


class PluginRuntimeType(str, Enum):
    """Runtime modes Nutria can use to expose plugin tools."""

    REMOTE_MCP = "remote_mcp"
    DECLARATIVE_API = "declarative_api"
    OPENAPI_BRIDGE = "openapi_bridge"
    SOAP_BRIDGE = "soap_bridge"


class PluginScope(str, Enum):
    """Scope where a plugin is installed."""

    PLATFORM = "platform"
    STORE = "store"
    PERSONA = "persona"


class ReviewableActionMode(str, Enum):
    """How a host-owned reviewable action addresses a channel resource."""

    NEW = "new"
    REPLY = "reply"


# The semantic vocabulary is deliberately small.  A plugin maps these stable
# names to its own MCP/API argument names; it must not invent a second host
# draft vocabulary.
class ReviewableActionField(str, Enum):
    """Stable host fields which may be mapped into a delivery tool."""

    RECIPIENT = "recipient"
    BODY = "body"
    SUBJECT = "subject"
    HTML_BODY = "html_body"
    REPLY_TARGET = "reply_target"
    SOURCE_REF = "source_ref"
    ORDER_ID = "order_id"
    AUDIT_CONTEXT = "audit_context"
    IDEMPOTENCY_KEY = "idempotency_key"
    SOURCE_FINGERPRINT = "source_fingerprint"
    THREAD_ID = "thread_id"
    CHANNEL = "channel"
    MODE = "mode"


class PreparationToolContract(BaseModel):
    """Optional pure adapter used to resolve a reply envelope.

    Preparation may read a connector and return structured provenance, but it
    can never persist a draft or perform an external write.
    """

    name: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    external_write: bool = False
    side_effect: str = Field(default="read", pattern=r"^(read|pure|none)$")

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _must_be_pure(self) -> "PreparationToolContract":
        if self.external_write:
            raise ValueError("preparation tools must be pure/read-only and cannot write externally")
        return self


class ReviewableActionContract(BaseModel):
    """Contract between ChatBotNutralia's draft store and a plugin delivery tool."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9\-]{0,63}$")
    kind: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_\-]*$")
    channel: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_\-]*$")
    modes: List[ReviewableActionMode] = Field(..., min_length=1)
    connection_id: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_\-]{0,127}$")
    execute_capability: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    prepare_capability: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    argument_map: Dict[ReviewableActionField, str]
    required_fields: List[ReviewableActionField] = Field(
        default_factory=lambda: [
            ReviewableActionField.RECIPIENT,
            ReviewableActionField.BODY,
        ]
    )
    editable_fields: List[ReviewableActionField] = Field(default_factory=list)
    immutable_fields: List[ReviewableActionField] = Field(
        default_factory=lambda: [
            ReviewableActionField.RECIPIENT,
            ReviewableActionField.SOURCE_REF,
            ReviewableActionField.REPLY_TARGET,
            ReviewableActionField.CHANNEL,
            ReviewableActionField.MODE,
        ]
    )

    model_config = {"extra": "forbid", "use_enum_values": True}

    @field_validator("required_fields", "editable_fields", "immutable_fields")
    @classmethod
    def _dedupe_enums(cls, value: List[Any]) -> List[Any]:
        result: List[Any] = []
        for item in value:
            if item not in result:
                result.append(item)
        return result

    @field_validator("argument_map")
    @classmethod
    def _validate_argument_map(cls, value: Dict[ReviewableActionField, str]) -> Dict[ReviewableActionField, str]:
        if not value:
            raise ValueError("argument_map cannot be empty")
        targets: set[str] = set()
        for semantic, target in value.items():
            target = str(target).strip()
            if not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_\-]{0,127}$", target):
                raise ValueError(f"unsafe plugin argument mapping for {semantic}: {target!r}")
            if target in targets:
                raise ValueError("argument_map cannot map multiple semantic fields to one argument")
            targets.add(target)
            value[semantic] = target
        return value

    @model_validator(mode="after")
    def _validate_contract(self) -> "ReviewableActionContract":
        if len(self.modes) != len(set(self.modes)):
            raise ValueError("modes must not contain duplicates")
        required = {_enum_value(field) for field in self.required_fields}
        mapped = {_enum_value(field) for field in self.argument_map}
        missing = required - mapped
        if missing:
            raise ValueError(
                "argument_map is missing required semantic fields: "
                + ", ".join(sorted(missing))
            )
        required_baseline = {
            ReviewableActionField.RECIPIENT.value,
            ReviewableActionField.BODY.value,
        }
        if not required_baseline.issubset(required):
            raise ValueError("required_fields must include recipient and body")
        # Every external delivery must be replay-safe.  The host always sends
        # the immutable action ID through this semantic field, so omitting it
        # would make an otherwise valid contract unsafe to execute.
        if ReviewableActionField.IDEMPOTENCY_KEY.value not in mapped:
            raise ValueError("argument_map must include idempotency_key")
        editable = {_enum_value(field) for field in self.editable_fields}
        immutable = {_enum_value(field) for field in self.immutable_fields}
        mandatory_immutable = {
            ReviewableActionField.RECIPIENT.value,
            ReviewableActionField.SOURCE_REF.value,
            ReviewableActionField.SOURCE_FINGERPRINT.value,
            ReviewableActionField.REPLY_TARGET.value,
            ReviewableActionField.THREAD_ID.value,
            ReviewableActionField.ORDER_ID.value,
            ReviewableActionField.CHANNEL.value,
            ReviewableActionField.MODE.value,
        }
        overlap = editable & (immutable | mandatory_immutable)
        if overlap:
            overlap_text = ", ".join(sorted(overlap))
            raise ValueError(f"fields cannot be both editable and immutable: {overlap_text}")
        if not editable.issubset(mapped):
            missing_editable = editable - mapped
            raise ValueError(
                "editable_fields must be present in argument_map: "
                + ", ".join(sorted(missing_editable))
            )
        if self.prepare_capability and self.prepare_capability == self.execute_capability:
            raise ValueError("preparation and execution capabilities must be different")
        return self

    def fingerprint(self) -> str:
        """Return a stable fingerprint used by the host for send-time checks."""
        payload = self.model_dump(mode="json", exclude_none=True)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

class PluginCompatibility(BaseModel):
    """Compatibility gates evaluated during install."""

    min_nutria_version: Optional[str] = None
    max_nutria_version: Optional[str] = None

    @field_validator("min_nutria_version", "max_nutria_version")
    @classmethod
    def _validate_semver(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not _SEMVER_RE.match(value):
            raise ValueError("compatibility versions must use semantic versioning")
        return value


class PluginPaths(BaseModel):
    """Relative paths used inside the plugin ZIP."""

    connections_dir: str = "connections"
    skills_dir: str = "skills"
    context_docs_dir: str = "context_docs"
    settings_schema: str = "settings.schema.json"
    hooks_file: str = "hooks/hooks.json"
    specs_dir: str = "specs"
    assets_dir: str = "assets"
    mcp_server_dir: str = "mcp_server"

    @field_validator(
        "connections_dir",
        "skills_dir",
        "context_docs_dir",
        "settings_schema",
        "hooks_file",
        "specs_dir",
        "assets_dir",
        "mcp_server_dir",
    )
    @classmethod
    def _validate_paths(cls, value: str) -> str:
        return _validate_relative_path(value)


class PluginAdminExtensionPlacement(str, Enum):
    """Admin UI locations where a plugin can mount host-rendered extensions."""

    PLUGINS_DETAIL = "plugins.detail"


class PluginAdminExtensionKind(str, Enum):
    """Host-rendered extension types supported by the admin frontend."""

    TABLE = "table"


class PluginAdminExtension(BaseModel):
    """Declarative admin/frontend extension exposed by a plugin."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9\-]*$", max_length=64)
    title: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    placement: PluginAdminExtensionPlacement = PluginAdminExtensionPlacement.PLUGINS_DETAIL
    kind: PluginAdminExtensionKind = PluginAdminExtensionKind.TABLE
    schema_path: str

    @field_validator("schema_path")
    @classmethod
    def _validate_schema_path(cls, value: str) -> str:
        path = _validate_relative_path(value)
        if not path.lower().endswith(".json"):
            raise ValueError("admin extension schema_path must point to a JSON file")
        return path


class PluginAdminFlowPlacement(str, Enum):
    """Admin UI locations where a plugin can mount host-rendered flows."""

    PLUGINS_DETAIL = "plugins.detail"


class PluginAdminFlowKind(str, Enum):
    """Host-rendered operator flow types supported by the admin frontend."""

    EXTERNAL_AUTH = "external_auth"


class PluginAdminFlow(BaseModel):
    """Declarative admin/operator flow exposed by a plugin."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9\-]*$", max_length=64)
    title: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)
    placement: PluginAdminFlowPlacement = PluginAdminFlowPlacement.PLUGINS_DETAIL
    kind: PluginAdminFlowKind = PluginAdminFlowKind.EXTERNAL_AUTH
    schema_path: str

    @field_validator("schema_path")
    @classmethod
    def _validate_schema_path(cls, value: str) -> str:
        path = _validate_relative_path(value)
        if not path.lower().endswith(".json"):
            raise ValueError("admin flow schema_path must point to a JSON file")
        return path


class PluginManifest(BaseModel):
    """Manifest stored in plugin.json — the single source of truth for plugin metadata."""

    schema_version: str = Field(..., pattern=r"^2\.0$")
    id: str = Field(..., pattern=r"^[a-z][a-z0-9\-]*$", max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(..., min_length=5, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)
    author: str = Field(..., min_length=1, max_length=128)
    runtime_types: List[PluginRuntimeType] = Field(default_factory=list, min_length=1)
    default_scope: PluginScope = PluginScope.STORE
    compatibility: PluginCompatibility = Field(default_factory=PluginCompatibility)
    paths: PluginPaths = Field(default_factory=PluginPaths)
    required_secrets: List[str] = Field(default_factory=list)
    optional_secrets: List[str] = Field(default_factory=list)
    remote_endpoints: List[str] = Field(default_factory=list)
    capabilities: List[CapabilityDescriptor] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    reviewable_actions: List[ReviewableActionContract] = Field(default_factory=list)
    admin_extensions: List[PluginAdminExtension] = Field(default_factory=list)
    admin_flows: List[PluginAdminFlow] = Field(default_factory=list)
    mcp_server_entry: Optional[str] = None  # e.g. "server.py" inside mcp_server_dir
    homepage: Optional[str] = None
    license: Optional[str] = None
    signature: Optional[str] = None  # hex-encoded ECDSA-P256 DER signature

    model_config = {"extra": "forbid"}

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not _SEMVER_RE.match(value):
            raise ValueError("plugin version must use semantic versioning")
        return value

    @field_validator("required_secrets", "optional_secrets", "tags")
    @classmethod
    def _dedupe_string_lists(cls, value: List[str]) -> List[str]:
        cleaned: List[str] = []
        for item in value:
            item = item.strip()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned

    @model_validator(mode="after")
    def _validate_capability_references(self) -> "PluginManifest":
        capability_ids = [capability.id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capabilities must not contain duplicate IDs")
        action_ids_list = [action.id for action in self.reviewable_actions]
        if len(action_ids_list) != len(set(action_ids_list)):
            raise ValueError("reviewable_actions must not contain duplicate contract IDs")
        capability_map = {capability.id: capability for capability in self.capabilities}
        action_ids = set(action_ids_list)
        for action in self.reviewable_actions:
            execute = capability_map.get(action.execute_capability)
            if execute is None:
                raise ValueError(
                    f"reviewable action {action.id!r} references unknown execution capability "
                    f"{action.execute_capability!r}"
                )
            if execute.effect != CapabilityEffect.EXTERNAL_WRITE:
                raise ValueError("reviewable execution capability must use external_write")
            if execute.model_callable:
                raise ValueError("reviewable execution capability must be host-only")
            if execute.connection_id != action.connection_id:
                raise ValueError("reviewable execution capability connection does not match action")
            if execute.reviewable_action_id != action.id:
                raise ValueError(
                    "reviewable execution capability must name its reviewable action"
                )
            execute_inputs = {
                str(item.semantic_field): item for item in execute.inputs
            }
            for semantic, target in action.argument_map.items():
                semantic_name = _enum_value(semantic)
                input_binding = execute_inputs.get(semantic_name)
                if input_binding is None:
                    raise ValueError(
                        f"argument_map semantic field {semantic_name!r} is not declared "
                        f"by execution capability {execute.id!r}"
                    )
                if input_binding.argument_name != target:
                    raise ValueError(
                        f"argument_map for {semantic_name!r} must use the capability "
                        f"argument {input_binding.argument_name!r}"
                    )
            missing_inputs = {
                str(item.semantic_field)
                for item in execute.inputs
                if item.required and str(item.semantic_field) not in action.argument_map
            }
            if missing_inputs:
                raise ValueError(
                    "argument_map is missing required execution inputs: "
                    + ", ".join(sorted(missing_inputs))
                )
            if action.prepare_capability:
                prepare = capability_map.get(action.prepare_capability)
                if prepare is None:
                    raise ValueError(
                        f"reviewable action {action.id!r} references unknown preparation capability "
                        f"{action.prepare_capability!r}"
                    )
                if prepare.effect != CapabilityEffect.PREPARE:
                    raise ValueError("reviewable preparation capability must use effect=prepare")
                if prepare.connection_id != action.connection_id:
                    raise ValueError(
                        "reviewable preparation capability connection does not match action"
                    )
        orphan_refs = {
            capability.reviewable_action_id
            for capability in self.capabilities
            if capability.reviewable_action_id
        } - action_ids
        if orphan_refs:
            raise ValueError("capabilities reference unknown reviewable action IDs")
        for capability in self.capabilities:
            if capability.reviewable_action_id:
                action = next(
                    item
                    for item in self.reviewable_actions
                    if item.id == capability.reviewable_action_id
                )
                if action.execute_capability != capability.id:
                    raise ValueError(
                        "reviewable_action_id may only be declared on the action execution capability"
                    )
        return self

    @field_validator("remote_endpoints")
    @classmethod
    def _validate_remote_endpoints(cls, value: List[str]) -> List[str]:
        import ipaddress
        from urllib.parse import urlparse

        endpoints: List[str] = []
        for item in value:
            parsed = urlparse(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("remote_endpoints must be absolute http/https URLs")
            # Block SSRF targets: localhost, loopback, private/link-local/reserved IP ranges.
            hostname = parsed.hostname or ""
            if hostname.lower() in ("localhost", "localhost.localdomain", ""):
                raise ValueError(
                    f"remote_endpoint {item!r} targets a private/internal address"
                )
            try:
                ip = ipaddress.ip_address(hostname)
            except ValueError:
                ip = None  # hostname (not IP literal) — cannot statically determine

            if ip is not None and (
                ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved
            ):
                raise ValueError(
                    f"remote_endpoint {item!r} targets a private/internal address"
                )
            if item not in endpoints:
                endpoints.append(item)
        return endpoints

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "PluginManifest":
        """Parse a plugin manifest from raw JSON bytes."""
        return cls.model_validate(json.loads(raw.decode("utf-8")))

    @classmethod
    def from_file(cls, path: Path) -> "PluginManifest":
        """Load a manifest from plugin.json on disk."""
        return cls.from_json_bytes(path.read_bytes())

    def to_file(self, path: Path) -> None:
        """Write this manifest to a plugin.json file."""
        path.write_text(
            json.dumps(self.model_dump(mode="json", exclude_none=True), indent=2) + "\n",
            encoding="utf-8",
        )
