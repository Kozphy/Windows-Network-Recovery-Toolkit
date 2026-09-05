"""Machine-readable endpoint failure taxonomy loader and integrity checks.

Loads ``configs/failure_taxonomy.yaml`` for research evaluation. This module does
not perform live diagnosis and does not authorize remediation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAXONOMY_PATH = REPO_ROOT / "configs" / "failure_taxonomy.yaml"

_REQUIRED_CLASS_FIELDS = (
    "id",
    "family",
    "name",
    "description",
    "observable_evidence",
    "expected_symptoms",
    "possible_confounders",
    "safe_remediation_candidates",
    "verification_requirements",
)


@dataclass(frozen=True)
class FailureClass:
    """One taxonomy class with stable ID (e.g. ``F_PROXY_004``)."""

    id: str
    family: str
    name: str
    description: str
    observable_evidence: tuple[str, ...]
    expected_symptoms: tuple[str, ...]
    possible_confounders: tuple[str, ...]
    safe_remediation_candidates: tuple[str, ...]
    verification_requirements: tuple[str, ...]
    incident_class_aliases: tuple[str, ...] = ()
    severity_default: str = "medium"
    compound: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "name": self.name,
            "description": self.description,
            "observable_evidence": list(self.observable_evidence),
            "expected_symptoms": list(self.expected_symptoms),
            "possible_confounders": list(self.possible_confounders),
            "safe_remediation_candidates": list(self.safe_remediation_candidates),
            "verification_requirements": list(self.verification_requirements),
            "incident_class_aliases": list(self.incident_class_aliases),
            "severity_default": self.severity_default,
            "compound": self.compound,
        }


@dataclass(frozen=True)
class FailureTaxonomy:
    """Loaded taxonomy document."""

    schema_version: str
    title: str
    description: str
    families: tuple[tuple[str, str], ...]
    classes: tuple[FailureClass, ...]
    source_path: Path | None = None
    _alias_index: dict[str, tuple[str, ...]] = field(default_factory=dict, repr=False)

    def get(self, class_id: str) -> FailureClass | None:
        for item in self.classes:
            if item.id == class_id:
                return item
        return None

    def ids_for_incident_class(self, incident_class: str) -> tuple[str, ...]:
        return self._alias_index.get(incident_class, ())

    def family_ids(self) -> frozenset[str]:
        return frozenset(fid for fid, _ in self.families)


def _as_str_tuple(value: Any, *, field_name: str, class_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{class_id}: {field_name} must be a list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{class_id}: {field_name} entries must be non-empty strings")
        out.append(item.strip())
    return tuple(out)


def _parse_class(raw: dict[str, Any]) -> FailureClass:
    missing = [k for k in _REQUIRED_CLASS_FIELDS if k not in raw]
    if missing:
        raise ValueError(f"taxonomy class missing fields {missing}: {raw.get('id')!r}")
    class_id = str(raw["id"]).strip()
    if not class_id.startswith("F_"):
        raise ValueError(f"taxonomy class id must start with F_: {class_id!r}")
    return FailureClass(
        id=class_id,
        family=str(raw["family"]).strip(),
        name=str(raw["name"]).strip(),
        description=str(raw["description"]).strip(),
        observable_evidence=_as_str_tuple(
            raw["observable_evidence"], field_name="observable_evidence", class_id=class_id
        ),
        expected_symptoms=_as_str_tuple(
            raw["expected_symptoms"], field_name="expected_symptoms", class_id=class_id
        ),
        possible_confounders=_as_str_tuple(
            raw["possible_confounders"], field_name="possible_confounders", class_id=class_id
        ),
        safe_remediation_candidates=_as_str_tuple(
            raw["safe_remediation_candidates"],
            field_name="safe_remediation_candidates",
            class_id=class_id,
        ),
        verification_requirements=_as_str_tuple(
            raw["verification_requirements"],
            field_name="verification_requirements",
            class_id=class_id,
        ),
        incident_class_aliases=_as_str_tuple(
            raw.get("incident_class_aliases") or [],
            field_name="incident_class_aliases",
            class_id=class_id,
        ),
        severity_default=str(raw.get("severity_default") or "medium").strip(),
        compound=bool(raw.get("compound", False)),
    )


def validate_taxonomy_dict(data: dict[str, Any]) -> list[str]:
    """Return a list of integrity errors (empty means valid)."""
    errors: list[str] = []
    if data.get("schema_version") != "failure_taxonomy.v1":
        errors.append("schema_version must be 'failure_taxonomy.v1'")
    families_raw = data.get("families")
    if not isinstance(families_raw, list) or not families_raw:
        errors.append("families must be a non-empty list")
        return errors
    family_ids: set[str] = set()
    for fam in families_raw:
        if not isinstance(fam, dict) or "id" not in fam or "name" not in fam:
            errors.append(f"invalid family entry: {fam!r}")
            continue
        fid = str(fam["id"])
        if fid in family_ids:
            errors.append(f"duplicate family id: {fid}")
        family_ids.add(fid)

    classes_raw = data.get("classes")
    if not isinstance(classes_raw, list) or not classes_raw:
        errors.append("classes must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for raw in classes_raw:
        if not isinstance(raw, dict):
            errors.append(f"class entry must be object: {raw!r}")
            continue
        try:
            parsed = _parse_class(raw)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if parsed.id in seen_ids:
            errors.append(f"duplicate class id: {parsed.id}")
        seen_ids.add(parsed.id)
        if parsed.family not in family_ids:
            errors.append(f"{parsed.id}: unknown family {parsed.family!r}")
        if not parsed.observable_evidence:
            errors.append(f"{parsed.id}: observable_evidence must be non-empty")
        if not parsed.verification_requirements:
            errors.append(f"{parsed.id}: verification_requirements must be non-empty")
        if not parsed.safe_remediation_candidates:
            errors.append(f"{parsed.id}: safe_remediation_candidates must be non-empty")
        if parsed.compound and parsed.family != "MIXED":
            errors.append(f"{parsed.id}: compound=true requires family MIXED")
    return errors


def load_taxonomy(path: Path | None = None) -> FailureTaxonomy:
    """Load and validate taxonomy YAML. Raises ``ValueError`` on integrity failure."""
    taxonomy_path = path or DEFAULT_TAXONOMY_PATH
    raw_text = taxonomy_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        raise ValueError(f"taxonomy root must be a mapping: {taxonomy_path}")
    errors = validate_taxonomy_dict(data)
    if errors:
        raise ValueError("taxonomy integrity failed:\n- " + "\n- ".join(errors))

    families = tuple(
        (str(item["id"]), str(item["name"])) for item in data["families"] if isinstance(item, dict)
    )
    classes = tuple(_parse_class(item) for item in data["classes"] if isinstance(item, dict))
    alias_index: dict[str, list[str]] = {}
    for cls in classes:
        for alias in cls.incident_class_aliases:
            alias_index.setdefault(alias, []).append(cls.id)
    frozen_index = {k: tuple(v) for k, v in alias_index.items()}
    return FailureTaxonomy(
        schema_version=str(data["schema_version"]),
        title=str(data.get("title") or ""),
        description=str(data.get("description") or ""),
        families=families,
        classes=classes,
        source_path=taxonomy_path,
        _alias_index=frozen_index,
    )


@lru_cache(maxsize=4)
def get_default_taxonomy() -> FailureTaxonomy:
    """Cached loader for the repository default taxonomy path."""
    return load_taxonomy(DEFAULT_TAXONOMY_PATH)


def clear_taxonomy_cache() -> None:
    get_default_taxonomy.cache_clear()
