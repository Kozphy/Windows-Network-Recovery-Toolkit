from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.knowledge.knowledge_models import KnowledgeBundle, KnowledgeEntry


def test_knowledge_entry_validates_id_pattern() -> None:
    with pytest.raises(ValidationError):
        KnowledgeEntry(entry_id="Bad-ID", category="network")


def test_knowledge_bundle_entry_key_mismatch() -> None:
    entry = KnowledgeEntry(entry_id="proxy_changed", category="network")
    with pytest.raises(ValidationError):
        KnowledgeBundle(
            knowledge_version="1.0.0",
            entries={"other_id": entry},
        )


def test_knowledge_bundle_rejects_unknown_schema() -> None:
    with pytest.raises(ValidationError):
        KnowledgeBundle(
            schema_version="knowledge.v0",  # type: ignore[arg-type]
            knowledge_version="1.0.0",
            entries={
                "proxy_changed": KnowledgeEntry(entry_id="proxy_changed", category="network"),
            },
        )
