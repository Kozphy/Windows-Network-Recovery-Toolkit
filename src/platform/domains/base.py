"""Domain adapter interface — collect events and evidence only."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.platform.models import DomainName, EvidenceItem, NormalizedEvent

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "domains"


class DomainAdapter(ABC):
    """Domains supply events and evidence; shared engines handle reasoning."""

    domain_name: DomainName

    @property
    def fixture_dir(self) -> Path:
        return FIXTURES_ROOT / self.domain_name

    def list_fixtures(self) -> list[str]:
        if not self.fixture_dir.is_dir():
            return []
        return sorted(p.name for p in self.fixture_dir.glob("*.json"))

    def load_fixture_blob(self, name: str | None = None) -> dict[str, Any]:
        files = self.list_fixtures()
        if not files:
            raise FileNotFoundError(f"No fixtures for {self.domain_name}")
        fname = name or files[0]
        return json.loads((self.fixture_dir / fname).read_text(encoding="utf-8"))

    def collect_events(self, fixture_name: str | None = None) -> list[NormalizedEvent]:
        fname = fixture_name or (self.list_fixtures()[0] if self.list_fixtures() else None)
        blob = self.load_fixture_blob(fname)
        event_data = blob.get("event") or blob
        ev = NormalizedEvent.model_validate(event_data)
        meta = dict(ev.metadata)
        if fname:
            meta["fixture"] = fname
        return [ev.model_copy(update={"metadata": meta})]

    @abstractmethod
    def build_evidence(self, event: NormalizedEvent) -> list[EvidenceItem]:
        ...
