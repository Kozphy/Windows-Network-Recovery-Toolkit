from __future__ import annotations

from src.platform.domains.base import DomainAdapter
from src.platform.models import EvidenceItem, NormalizedEvent


class FixtureEvidenceAdapter(DomainAdapter):
    """Default build_evidence from fixture JSON."""

    def build_evidence(self, event: NormalizedEvent) -> list[EvidenceItem]:
        rows = self.load_fixture_blob(event.metadata.get("fixture")).get("evidence") or []
        out: list[EvidenceItem] = []
        for row in rows:
            data = dict(row)
            data["event_id"] = event.event_id
            data.setdefault("timestamp_utc", event.timestamp_utc)
            out.append(EvidenceItem.model_validate(data))
        return out
