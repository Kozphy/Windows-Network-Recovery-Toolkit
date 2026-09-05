"""SKILL.md loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from riskclaw.schemas import SkillRiskLevel
from riskclaw.skills import SkillLoader, SkillLoadError

VALID_SKILL = """---
name: proxy-risk-investigation
description: Diagnose Windows proxy drift using deterministic evidence.
allowed_tools:
  - proxy.collect
  - proxy.classify
risk_level: read_only
requires_human_approval: false
---

# Proxy Risk Investigation

Collect evidence before classification. Preserve limitations.
"""


def _write_skill(root: Path, directory: str, content: str = VALID_SKILL) -> Path:
    skill_dir = root / directory
    skill_dir.mkdir()
    source = skill_dir / "SKILL.md"
    source.write_text(content, encoding="utf-8")
    return source


def test_load_skill_with_strict_frontmatter(tmp_path: Path) -> None:
    source = _write_skill(tmp_path, "proxy-risk-investigation")
    loader = SkillLoader(known_tools={"proxy.collect", "proxy.classify"})

    skill = loader.load(source)

    assert skill.name == "proxy-risk-investigation"
    assert skill.risk_level is SkillRiskLevel.READ_ONLY
    assert "Collect evidence before classification." in skill.instructions


def test_skill_referencing_unknown_tool_is_rejected(tmp_path: Path) -> None:
    source = _write_skill(tmp_path, "proxy-risk-investigation")

    with pytest.raises(SkillLoadError, match="unregistered tools"):
        SkillLoader(known_tools={"proxy.collect"}).load(source)


def test_missing_frontmatter_is_rejected(tmp_path: Path) -> None:
    source = _write_skill(tmp_path, "invalid", "# No frontmatter")

    with pytest.raises(SkillLoadError, match="frontmatter"):
        SkillLoader().load(source)


def test_unknown_frontmatter_field_is_rejected(tmp_path: Path) -> None:
    source = _write_skill(
        tmp_path,
        "invalid",
        VALID_SKILL.replace("requires_human_approval: false", "autonomous_execution: true"),
    )

    with pytest.raises(SkillLoadError, match="invalid skill contract"):
        SkillLoader().load(source)


def test_discover_is_stable_and_sorted(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "b-skill",
        VALID_SKILL.replace(
            "name: proxy-risk-investigation",
            "name: tls-path-analysis",
        ),
    )
    _write_skill(tmp_path, "a-skill")

    skills = SkillLoader().discover(tmp_path)

    assert [skill.name for skill in skills] == [
        "proxy-risk-investigation",
        "tls-path-analysis",
    ]
