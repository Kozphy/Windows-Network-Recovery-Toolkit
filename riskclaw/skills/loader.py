"""Load strict RiskClaw skills from YAML-frontmatter SKILL.md files."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from riskclaw.schemas import SkillDefinition

_FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<metadata>.*?)\r?\n---[ \t]*(?:\r?\n|$)(?P<body>.*)\Z",
    re.DOTALL,
)


class SkillLoadError(ValueError):
    pass


class SkillLoader:
    """Discover skills and reject malformed or unknown-tool allowlists."""

    def __init__(self, *, known_tools: Iterable[str] | None = None) -> None:
        self._known_tools = frozenset(known_tools) if known_tools is not None else None

    def load(self, path: str | Path) -> SkillDefinition:
        source = Path(path)
        if source.is_dir():
            source = source / "SKILL.md"
        if not source.is_file():
            raise SkillLoadError(f"SKILL.md not found: {source}")

        text = source.read_text(encoding="utf-8")
        match = _FRONTMATTER.match(text)
        if match is None:
            raise SkillLoadError(f"missing or malformed YAML frontmatter: {source}")

        try:
            metadata = yaml.safe_load(match.group("metadata"))
        except yaml.YAMLError as exc:
            raise SkillLoadError(f"invalid YAML frontmatter: {source}") from exc

        if not isinstance(metadata, dict):
            raise SkillLoadError(f"skill frontmatter must be a mapping: {source}")

        body = match.group("body").strip()
        raw: dict[str, Any] = {
            **metadata,
            "instructions": body,
            "source_path": source.as_posix(),
        }
        try:
            skill = SkillDefinition.model_validate(raw)
        except ValidationError as exc:
            raise SkillLoadError(f"invalid skill contract: {source}: {exc}") from exc

        if self._known_tools is not None:
            unknown = sorted(set(skill.allowed_tools) - self._known_tools)
            if unknown:
                raise SkillLoadError(f"skill references unregistered tools: {', '.join(unknown)}")
        return skill

    def discover(self, root: str | Path) -> tuple[SkillDefinition, ...]:
        directory = Path(root)
        if not directory.is_dir():
            raise SkillLoadError(f"skill directory not found: {directory}")

        skills: list[SkillDefinition] = []
        names: set[str] = set()
        for source in sorted(directory.glob("*/SKILL.md")):
            skill = self.load(source)
            if skill.name in names:
                raise SkillLoadError(f"duplicate skill name: {skill.name}")
            names.add(skill.name)
            skills.append(skill)
        return tuple(skills)
