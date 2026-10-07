"""SKILL.md frontmatter contract.

A skill is procedural guidance. It has no trigger, routing or authority fields: the Agent
chooses to load it. Unknown frontmatter keys (including the removed ``triggers``) are
rejected so a plugin cannot silently ship dead routing hints.
"""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field

SKILL_FILENAME = "SKILL.md"


class SkillFrontmatter(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9\-]*$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    description: str = Field(..., min_length=1, max_length=1024)
    always_active: bool = False
    capabilities_required: list[str] = Field(default_factory=list)
    provider_ids: list[str] = Field(default_factory=list)
    connection_id: str | None = None
    requires_verified_connection: bool = False
    fresh_source_capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


def parse_skill_frontmatter(content: str) -> SkillFrontmatter:
    """Parse and validate the frontmatter of one SKILL.md document."""
    if not content.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md frontmatter is not terminated")
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    return SkillFrontmatter.model_validate(data)
