"""In-memory knowledge registry — deterministic lookup and replay snapshots.

Wraps a validated :class:`KnowledgeBundle` with digest-backed lookup helpers.
Does not hot-reload files — construct a new registry after knowledge file changes.
"""

from __future__ import annotations

from pathlib import Path

from .knowledge_loader import (
    bundle_content_digest,
    default_knowledge_path,
    load_knowledge_directory,
    load_knowledge_path,
    load_knowledge_text,
)
from .knowledge_models import KnowledgeBundle, KnowledgeEntry, KnowledgeRegistrySnapshot


class KnowledgeRegistry:
    """Replayable registry over a validated :class:`KnowledgeBundle`."""

    def __init__(self, bundle: KnowledgeBundle, *, content_digest: str | None = None) -> None:
        self._bundle = bundle
        self._digest = content_digest or bundle_content_digest(bundle)
        self._entries = dict(sorted(bundle.entries.items()))

    @classmethod
    def from_bundle(cls, bundle: KnowledgeBundle) -> KnowledgeRegistry:
        return cls(bundle)

    @classmethod
    def from_path(cls, path: Path) -> KnowledgeRegistry:
        return cls(load_knowledge_path(path))

    @classmethod
    def from_directory(cls, directory: Path) -> KnowledgeRegistry:
        return cls(load_knowledge_directory(directory))

    @classmethod
    def from_text(cls, text: str, *, source_path: str = "") -> KnowledgeRegistry:
        return cls(load_knowledge_text(text, source_path=source_path))

    @classmethod
    def from_default(cls, repo_root: Path | None = None) -> KnowledgeRegistry:
        return cls.from_path(default_knowledge_path(repo_root))

    @property
    def bundle(self) -> KnowledgeBundle:
        return self._bundle

    @property
    def knowledge_version(self) -> str:
        return self._bundle.knowledge_version

    @property
    def schema_version(self) -> str:
        return self._bundle.schema_version

    def content_digest(self) -> str:
        return self._digest

    def entry_ids(self) -> list[str]:
        return list(self._entries.keys())

    def categories(self) -> list[str]:
        return sorted({entry.category for entry in self._entries.values()})

    def get(self, entry_id: str) -> KnowledgeEntry:
        try:
            return self._entries[entry_id]
        except KeyError as exc:
            raise KeyError(f"unknown knowledge entry: {entry_id}") from exc

    def try_get(self, entry_id: str) -> KnowledgeEntry | None:
        return self._entries.get(entry_id)

    def list_by_category(self, category: str) -> list[KnowledgeEntry]:
        cat = category.strip().lower()
        return [entry for entry in self._entries.values() if entry.category.lower() == cat]

    def common_causes_for(self, entry_id: str) -> list[str]:
        return list(self.get(entry_id).common_causes)

    def snapshot(self) -> KnowledgeRegistrySnapshot:
        return KnowledgeRegistrySnapshot(
            knowledge_version=self._bundle.knowledge_version,
            source_paths=[self._bundle.source_path] if self._bundle.source_path else [],
            entry_ids=self.entry_ids(),
            content_digest=self._digest,
            entries=self._entries,
        )
