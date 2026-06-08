from __future__ import annotations

from pathlib import Path

import pytest

from src.knowledge.knowledge_loader import (
    bundle_content_digest,
    load_knowledge_directory,
    load_knowledge_path,
    load_knowledge_text,
    parse_knowledge_document,
)


def test_load_default_knowledge_file(knowledge_fixture_path: Path) -> None:
    bundle = load_knowledge_path(knowledge_fixture_path)
    assert bundle.schema_version == "knowledge.v1"
    assert bundle.knowledge_version == "2026.06.04"
    entry = bundle.entries["proxy_changed"]
    assert entry.category == "network"
    assert entry.common_causes == ["developer_proxy", "security_tool", "malware"]


def test_shorthand_document_without_entries_key() -> None:
    document = {
        "schema_version": "knowledge.v1",
        "knowledge_version": "1.0.0",
        "proxy_changed": {
            "category": "network",
            "common_causes": ["developer_proxy"],
        },
    }
    bundle = parse_knowledge_document(document)
    assert "proxy_changed" in bundle.entries


def test_missing_knowledge_version_rejected() -> None:
    with pytest.raises(ValueError, match="knowledge_version"):
        parse_knowledge_document({"schema_version": "knowledge.v1", "entries": {}})


def test_invalid_schema_version_file() -> None:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "knowledge" / "invalid" / "invalid_version.yaml"
    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_knowledge_path(path)


def test_deterministic_digest_stable(knowledge_fixture_path: Path) -> None:
    bundle = load_knowledge_path(knowledge_fixture_path)
    assert bundle_content_digest(bundle) == bundle_content_digest(bundle)


def test_load_directory_merge_deterministic(knowledge_dir: Path) -> None:
    bundle = load_knowledge_directory(knowledge_dir)
    assert set(bundle.entries) == {"alpha_entry", "beta_entry"}
    assert bundle.entries["alpha_entry"].common_causes == ["cause_a"]


def test_minimal_yaml_text_loader_without_entries_wrapper() -> None:
    text = """
schema_version: knowledge.v1
knowledge_version: "1.0.0"
entries:
  proxy_changed:
    category: network
    common_causes:
      - developer_proxy
      - security_tool
"""
    bundle = load_knowledge_text(text)
    assert bundle.entries["proxy_changed"].common_causes == ["developer_proxy", "security_tool"]
