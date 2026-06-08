from __future__ import annotations

from pathlib import Path

import pytest

from src.knowledge.knowledge_registry import KnowledgeRegistry


def test_registry_lookup_proxy_changed(knowledge_fixture_path: Path) -> None:
    registry = KnowledgeRegistry.from_path(knowledge_fixture_path)
    entry = registry.get("proxy_changed")
    assert entry.category == "network"
    assert "malware" in entry.common_causes


def test_registry_unknown_entry(knowledge_fixture_path: Path) -> None:
    registry = KnowledgeRegistry.from_path(knowledge_fixture_path)
    with pytest.raises(KeyError, match="unknown knowledge entry"):
        registry.get("not_real")


def test_registry_list_by_category(knowledge_fixture_path: Path) -> None:
    registry = KnowledgeRegistry.from_path(knowledge_fixture_path)
    network_entries = registry.list_by_category("network")
    assert len(network_entries) >= 2
    assert all(e.category == "network" for e in network_entries)


def test_registry_common_causes_for(knowledge_fixture_path: Path) -> None:
    registry = KnowledgeRegistry.from_path(knowledge_fixture_path)
    causes = registry.common_causes_for("proxy_changed")
    assert causes[0] == "developer_proxy"


def test_registry_snapshot_replay_fields(knowledge_fixture_path: Path) -> None:
    registry = KnowledgeRegistry.from_path(knowledge_fixture_path)
    snap_a = registry.snapshot()
    snap_b = registry.snapshot()
    assert snap_a.content_digest == snap_b.content_digest
    assert snap_a.entry_ids == snap_b.entry_ids
    assert len(snap_a.content_digest) == 64


def test_registry_from_default() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = KnowledgeRegistry.from_default(root)
    assert registry.try_get("proxy_changed") is not None
