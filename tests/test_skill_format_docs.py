from pathlib import Path


def test_skill_format_documents_capability_guidance_without_legacy_authority_fields():
    content = (Path(__file__).parents[1] / "docs" / "skill-format.md").read_text()

    assert "capabilities_required" in content
    assert "provider_ids" in content
    assert "## Where behavior belongs" in content
    assert "Capabilities whose knowledge/use this guidance depends on" in content
    assert "does not grant a capability" in content
    assert "external_write" in content
    assert "prepared_action" in content
    assert "tools_required:" not in content
    assert "authority_levels:" not in content
    assert "Requires approval" not in content
    assert "execute_prepared_action" not in content
