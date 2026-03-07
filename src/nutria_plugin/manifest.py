"""
Plugin manifest models for Nutria plugins.

These models are the canonical schema for plugin.json and are shared between
the SDK (for plugin authors) and the ChatBotNutralia runtime (for validation
at install time).
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


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

    @field_validator(
        "connections_dir",
        "skills_dir",
        "context_docs_dir",
        "settings_schema",
        "hooks_file",
        "specs_dir",
        "assets_dir",
    )
    @classmethod
    def _validate_paths(cls, value: str) -> str:
        return _validate_relative_path(value)


class PluginManifest(BaseModel):
    """Manifest stored in plugin.json — the single source of truth for plugin metadata."""

    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
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
    remote_endpoints: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
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

    @field_validator("required_secrets", "capabilities", "tags")
    @classmethod
    def _dedupe_string_lists(cls, value: List[str]) -> List[str]:
        cleaned: List[str] = []
        for item in value:
            item = item.strip()
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned

    @field_validator("remote_endpoints")
    @classmethod
    def _validate_remote_endpoints(cls, value: List[str]) -> List[str]:
        from urllib.parse import urlparse

        endpoints: List[str] = []
        for item in value:
            parsed = urlparse(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("remote_endpoints must be absolute http/https URLs")
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
