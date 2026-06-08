"""Infrastructure domain adapter — SRE capacity and circuit-breaker signals.

Signals: CPU saturation, circuit breaker state, SLO burn rate. Outputs throttle/page
candidates — does not page on-call or shed traffic automatically.
"""

from __future__ import annotations

from typing import Any

from ..adapter import AdapterContext, DomainAdapter
from ..models import Evidence, Observation, PlatformDomain


class InfrastructureAdapter(DomainAdapter):
    """Adapter for infrastructure capacity and reliability preview decisions."""

    @property
    def domain(self) -> PlatformDomain:
        return PlatformDomain.INFRASTRUCTURE

    def collect_observations(self, context: AdapterContext) -> list[Observation]:
        payload = context.payload
        return [
            Observation(
                domain=self.domain.value,
                signal="cpu_saturation",
                value=float(payload.get("cpu_pct", 82.0)),
                confidence=0.85,
                source_ref="fixture:node_exporter",
            ),
            Observation(
                domain=self.domain.value,
                signal="circuit_breaker_open",
                value=bool(payload.get("circuit_open", False)),
                confidence=0.9,
            ),
            Observation(
                domain=self.domain.value,
                signal="slo_burn_rate",
                value=float(payload.get("burn_rate", 2.4)),
                confidence=0.7,
            ),
        ]

    def derive_evidence(self, observations: list[Observation]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for obs in observations:
            supports = True
            if obs.signal == "cpu_saturation" and float(obs.value) > 80:
                supports = True
            if obs.signal == "circuit_breaker_open" and obs.value:
                supports = False
            evidence.append(
                Evidence(
                    evidence_id=f"infra_{obs.signal}",
                    domain=self.domain.value,
                    label=f"{obs.signal}={obs.value}",
                    kind="observation",
                    weight=0.65,
                    supports_decision=supports,
                    observation_ids=[obs.observation_id],
                )
            )
        return evidence

    def build_candidate_specs(self, context: AdapterContext) -> list[dict[str, Any]]:
        return [
            {
                "decision_id": "infra_throttle_traffic",
                "label": "Apply traffic throttle / load shed",
                "base_benefit": 52.0,
                "base_risk": 25.0,
            },
            {
                "decision_id": "infra_page_oncall",
                "label": "Page on-call for capacity review",
                "base_benefit": 45.0,
                "base_risk": 10.0,
            },
        ]
