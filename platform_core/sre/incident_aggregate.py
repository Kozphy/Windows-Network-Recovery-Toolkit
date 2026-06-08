"""Event-sourced incident aggregate — lifecycle commands emit domain events only."""

from __future__ import annotations

from typing import Any

from platform_core.reasoning_models import new_id

from .event_store import DomainEventStore, append_domain_event
from .models import (
    DomainEvent,
    DomainEventType,
    FailureDomainName,
    IncidentPhase,
    IncidentProjection,
)
from .projector import rebuild_incident


class IncidentAggregate:
    """Command handler for incident lifecycle — no mutable state, events only."""

    def __init__(self, incident_id: str, *, store: DomainEventStore | None = None) -> None:
        self.incident_id = incident_id
        self._store = store or DomainEventStore()

    @property
    def projection(self) -> IncidentProjection:
        return rebuild_incident(self.incident_id, store=self._store)

    def _append(
        self,
        event_type: DomainEventType,
        payload: dict[str, Any],
        *,
        causation_id: str | None = None,
        actor: str = "system",
        failure_domain: FailureDomainName | None = None,
    ) -> DomainEvent:
        return append_domain_event(
            aggregate_id=self.incident_id,
            aggregate_type="incident",
            event_type=event_type,
            correlation_id=self.incident_id,
            payload=payload,
            causation_id=causation_id,
            failure_domain=failure_domain,
            actor=actor,
            store=self._store,
        )

    @classmethod
    def open(
        cls,
        *,
        endpoint_id: str,
        title: str,
        severity: str = "medium",
        trigger_event_ids: list[str] | None = None,
        limitations: list[str] | None = None,
        store: DomainEventStore | None = None,
    ) -> IncidentAggregate:
        incident_id = new_id("inc")
        agg = cls(incident_id, store=store)
        agg._append(
            "incident.detected",
            {
                "endpoint_id": endpoint_id,
                "title": title,
                "severity": severity,
                "trigger_event_ids": trigger_event_ids or [],
                "limitations": limitations
                or ["Observation != Proof; incident opened on correlated signals only."],
            },
            failure_domain="telemetry_ingest",
        )
        return agg

    def acknowledge(self, *, actor: str = "operator") -> DomainEvent:
        proj = self.projection
        if proj.phase not in (IncidentPhase.DETECTED,):
            raise ValueError(f"cannot acknowledge from phase {proj.phase}")
        return self._append("incident.acknowledged", {"actor": actor}, actor=actor)

    def start_investigation(self, *, actor: str = "operator") -> DomainEvent:
        proj = self.projection
        if proj.phase not in (IncidentPhase.DETECTED, IncidentPhase.ACKNOWLEDGED):
            raise ValueError(f"cannot start investigation from phase {proj.phase}")
        return self._append(
            "incident.investigation_started",
            {"actor": actor},
            actor=actor,
            failure_domain="investigation",
        )

    def record_hypothesis_ranking(
        self,
        *,
        run_id: str,
        accepted_hypothesis: str,
        state_path: list[str],
        event_ids: list[str],
        policy_outcome: str,
        causation_id: str | None = None,
    ) -> DomainEvent:
        return self._append(
            "incident.hypothesis_ranked",
            {
                "run_id": run_id,
                "accepted_hypothesis": accepted_hypothesis,
                "state_path": state_path,
                "event_ids": event_ids,
                "policy_outcome": policy_outcome,
            },
            causation_id=causation_id,
            failure_domain="hypothesis_engine",
        )

    def identify_root_cause(
        self,
        *,
        root_cause_summary: str,
        accepted_hypothesis: str,
        confidence_tier: str,
        evidence_event_ids: list[str],
        limitations: list[str],
        actor: str = "investigation",
    ) -> DomainEvent:
        proj = self.projection
        if proj.phase not in (
            IncidentPhase.INVESTIGATING,
            IncidentPhase.ROOT_CAUSE_IDENTIFIED,
        ):
            raise ValueError(f"cannot identify root cause from phase {proj.phase}")
        if confidence_tier not in ("proven", "contrast_tested") and "malware" in accepted_hypothesis.lower():
            limitations = list(limitations) + [
                "Malware-class hypothesis without proof tier — statement is investigative, not conviction."
            ]
        return self._append(
            "incident.root_cause_identified",
            {
                "root_cause_summary": root_cause_summary,
                "accepted_hypothesis": accepted_hypothesis,
                "confidence_tier": confidence_tier,
                "evidence_event_ids": evidence_event_ids,
                "limitations": limitations,
            },
            actor=actor,
            failure_domain="investigation",
        )

    def attempt_mitigation(self, *, action: str, outcome: str, actor: str = "operator") -> DomainEvent:
        return self._append(
            "incident.mitigation_attempted",
            {"action": action, "outcome": outcome, "actor": actor},
            actor=actor,
            failure_domain="remediation",
        )

    def resolve(self, *, resolution: str, actor: str = "operator") -> DomainEvent:
        proj = self.projection
        if proj.phase == IncidentPhase.RESOLVED:
            raise ValueError("incident already resolved")
        return self._append(
            "incident.resolved",
            {"resolution": resolution, "actor": actor},
            actor=actor,
        )

    def mark_false_positive(self, *, reason: str, actor: str = "operator") -> DomainEvent:
        return self._append(
            "incident.false_positive",
            {"reason": reason, "actor": actor},
            actor=actor,
        )
