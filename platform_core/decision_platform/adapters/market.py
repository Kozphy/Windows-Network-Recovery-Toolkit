"""Market events domain adapter — catalyst calendar research (no trade execution).

Loads calendar rows from ``fixtures/market_events/calendar.json`` (or
``context.fixture_path``). Research signals only — does not place orders or move capital.
Does not depend on the archived ``src.market_events`` package.

Input assumptions:
    ``payload["event_id"]`` defaults to ``CPI_2026_06``.
    ``fixture_path`` overrides default calendar location when set on context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..adapter import AdapterContext, DomainAdapter
from ..models import Evidence, Observation, PlatformDomain

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CALENDAR = _REPO_ROOT / "fixtures" / "market_events" / "calendar.json"


def _load_event(event_id: str, calendar_path: Path | None) -> dict[str, Any]:
    path = calendar_path if calendar_path is not None else _DEFAULT_CALENDAR
    if not path.is_file():
        return {
            "event_id": event_id,
            "confidence": 0.0,
            "source": "missing_source",
            "expected_volatility": "unknown",
            "direction_bias": "neutral",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    events = data.get("events") if isinstance(data, dict) else data
    if not isinstance(events, list):
        events = []
    for row in events:
        if isinstance(row, dict) and str(row.get("event_id") or "") == event_id:
            return row
    return {
        "event_id": event_id,
        "confidence": 0.0,
        "source": "missing_source",
        "expected_volatility": "unknown",
        "direction_bias": "neutral",
    }


def _field(event: dict[str, Any], key: str, default: str = "") -> str:
    value = event.get(key, default)
    if isinstance(value, dict):
        return str(value.get("value") or value.get("name") or default)
    return str(value if value is not None else default)


class MarketAdapter(DomainAdapter):
    """Adapter for macro/crypto calendar catalyst research decisions."""

    @property
    def domain(self) -> PlatformDomain:
        return PlatformDomain.MARKET_EVENTS

    def collect_observations(self, context: AdapterContext) -> list[Observation]:
        event_id = context.payload.get("event_id", "CPI_2026_06")
        calendar_path = Path(context.fixture_path) if context.fixture_path else None
        event = _load_event(str(event_id), calendar_path)
        confidence = float(event.get("confidence") or 0.0)
        source = _field(event, "source", "missing_source") or "missing_source"
        return [
            Observation(
                domain=self.domain.value,
                signal="calendar_event",
                value=event.get("event_id") or event_id,
                confidence=confidence,
                source_ref=source,
            ),
            Observation(
                domain=self.domain.value,
                signal="expected_volatility",
                value=_field(event, "expected_volatility", "unknown"),
                confidence=0.7,
            ),
            Observation(
                domain=self.domain.value,
                signal="direction_bias",
                value=_field(event, "direction_bias", "neutral"),
                confidence=0.6,
            ),
        ]

    def derive_evidence(self, observations: list[Observation]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for obs in observations:
            weight = 0.65 if obs.signal == "calendar_event" else 0.5
            supports = True
            if obs.signal == "calendar_event" and obs.source_ref in ("", "missing_source"):
                supports = False
            evidence.append(
                Evidence(
                    evidence_id=f"mkt_{obs.signal}",
                    domain=self.domain.value,
                    label=f"{obs.signal}={obs.value}",
                    kind="observation",
                    weight=weight,
                    supports_decision=supports,
                    observation_ids=[obs.observation_id],
                )
            )
        return evidence

    def build_candidate_specs(self, context: AdapterContext) -> list[dict[str, Any]]:
        event_id = context.payload.get("event_id", "CPI_2026_06")
        return [
            {
                "decision_id": f"mkt_thesis_{event_id}",
                "label": f"Publish research thesis for {event_id}",
                "base_benefit": 55.0,
                "base_risk": 20.0,
            },
            {
                "decision_id": f"mkt_monitor_{event_id}",
                "label": f"Monitor only — {event_id}",
                "base_benefit": 35.0,
                "base_risk": 8.0,
            },
        ]
