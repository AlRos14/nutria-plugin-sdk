"""Tests for PluginManifest model."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from nutria_plugin.manifest import PluginManifest, PluginRuntimeType, PluginScope


def _minimal_manifest(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "Tester",
        "runtime_types": ["declarative_api"],
    }
    base.update(overrides)
    return base


def test_minimal_manifest_parses():
    m = PluginManifest.model_validate(_minimal_manifest())
    assert m.id == "test-plugin"
    assert m.version == "1.0.0"
    assert m.default_scope == PluginScope.STORE
    assert m.runtime_types == [PluginRuntimeType.DECLARATIVE_API]


def test_all_runtime_types_accepted():
    for rt in PluginRuntimeType:
        m = PluginManifest.model_validate(_minimal_manifest(runtime_types=[rt.value]))
        assert m.runtime_types == [rt]


def test_invalid_id_rejects():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_minimal_manifest(id="InvalidID"))


def test_id_with_underscore_rejected():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_minimal_manifest(id="my_plugin"))


def test_id_with_hyphen_accepted():
    m = PluginManifest.model_validate(_minimal_manifest(id="my-plugin"))
    assert m.id == "my-plugin"


def test_version_must_be_semver():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_minimal_manifest(version="1.0"))


def test_schema_version_must_be_1_0():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_minimal_manifest(schema_version="2.0"))


def test_empty_runtime_types_rejected():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(_minimal_manifest(runtime_types=[]))


def test_extra_fields_rejected():
    data = _minimal_manifest()
    data["unexpected_field"] = "oops"
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(data)


def test_required_secrets_deduplicated():
    m = PluginManifest.model_validate(
        _minimal_manifest(required_secrets=["KEY", "KEY", "OTHER"])
    )
    assert m.required_secrets == ["KEY", "OTHER"]


def test_remote_endpoints_must_be_https():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(
            _minimal_manifest(remote_endpoints=["ftp://example.com"])
        )


def test_remote_endpoints_accept_http_and_https():
    m = PluginManifest.model_validate(
        _minimal_manifest(
            remote_endpoints=["https://api.trello.com", "http://internal.lan/api"]
        )
    )
    assert len(m.remote_endpoints) == 2


def test_from_json_bytes_roundtrip(tmp_path):
    m = PluginManifest.model_validate(_minimal_manifest())
    out = tmp_path / "plugin.json"
    m.to_file(out)
    m2 = PluginManifest.from_file(out)
    assert m.id == m2.id
    assert m.version == m2.version


def test_signature_field_accepted():
    data = _minimal_manifest()
    data["signature"] = "deadbeef"
    m = PluginManifest.model_validate(data)
    assert m.signature == "deadbeef"


def test_signature_field_excluded_from_none_dump():
    m = PluginManifest.model_validate(_minimal_manifest())
    dump = m.model_dump(mode="json", exclude_none=True)
    assert "signature" not in dump
