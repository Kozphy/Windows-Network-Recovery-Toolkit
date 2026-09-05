"""Integrity tests for the endpoint failure taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from research.taxonomy import (
    DEFAULT_TAXONOMY_PATH,
    clear_taxonomy_cache,
    get_default_taxonomy,
    load_taxonomy,
    validate_taxonomy_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LABEL_SCHEMA = REPO_ROOT / "benchmarks" / "dataset_v1" / "label_schema.json"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_taxonomy_cache()
    yield
    clear_taxonomy_cache()


def test_default_taxonomy_path_exists() -> None:
    assert DEFAULT_TAXONOMY_PATH.is_file()


def test_load_default_taxonomy() -> None:
    tax = load_taxonomy()
    assert tax.schema_version == "failure_taxonomy.v1"
    assert len(tax.classes) >= 20
    proxy_dead = tax.get("F_PROXY_004")
    assert proxy_dead is not None
    assert proxy_dead.compound is False
    mixed = tax.get("F_MIXED_001")
    assert mixed is not None
    assert mixed.compound is True
    assert "DEAD_PROXY_CONFIG" in proxy_dead.incident_class_aliases


def test_ids_unique_and_families_valid() -> None:
    tax = get_default_taxonomy()
    ids = [c.id for c in tax.classes]
    assert len(ids) == len(set(ids))
    family_ids = tax.family_ids()
    for cls in tax.classes:
        assert cls.family in family_ids
        assert cls.id.startswith("F_")
        assert cls.observable_evidence
        assert cls.safe_remediation_candidates
        assert cls.verification_requirements


def test_validate_rejects_duplicate_id() -> None:
    data = yaml.safe_load(DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8"))
    data["classes"].append(dict(data["classes"][0]))
    errors = validate_taxonomy_dict(data)
    assert any("duplicate class id" in e for e in errors)


def test_validate_rejects_unknown_family() -> None:
    data = yaml.safe_load(DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8"))
    data["classes"][0]["family"] = "NOT_A_FAMILY"
    errors = validate_taxonomy_dict(data)
    assert any("unknown family" in e for e in errors)


def test_incident_aliases_cover_benchmark_label_schema() -> None:
    """Every benchmark incident class should map to at least one taxonomy id."""
    tax = load_taxonomy()
    schema = json.loads(LABEL_SCHEMA.read_text(encoding="utf-8"))
    incident_classes = schema["incident_classes"]
    missing = [c for c in incident_classes if not tax.ids_for_incident_class(c)]
    assert missing == [], f"unmapped incident classes: {missing}"


def test_alias_index_lookup() -> None:
    tax = load_taxonomy()
    ids = tax.ids_for_incident_class("WININET_WINHTTP_MISMATCH")
    assert "F_PROXY_003" in ids
