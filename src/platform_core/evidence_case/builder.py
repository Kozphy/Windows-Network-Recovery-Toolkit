"""Build Evidence Case from fixtures or structured input."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from platform_core.models import utc_now_iso
from src.platform_core.contracts import (
    AuditRecord,
    EvidenceBundle,
    EvidenceItem,
    Hypothesis,
    IncidentOutcome,
    LearningRecord,
)
from src.platform_core.decision.engine import build_decision
from src.platform_core.policy.engine import evaluate_policy

from .models import (
    AuditStage,
    DecisionStage,
    EvidenceCase,
    EvidenceStage,
    ExecutionStage,
    HypothesisStage,
    LearningStage,
    ObservationStage,
    OutcomeStage,
    RiskAssessmentStage,
    ValidationAttempt,
    ValidationStage,
)

_EPISTEMIC_LIMITATIONS = [
    "Observation is not proof.",
    "Correlation is not causation.",
    "Confidence is not certainty.",
    "Policy permission is not a safety guarantee.",
]


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _evidence_items_from_fixture(data: dict[str, Any], incident_id: str) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    proxy = data.get("proxy_state") or {}
    owner = data.get("proxy_owner") or {}
    classification = data.get("classification") or {}
    signals = {
        "wininet_proxy_enabled": proxy.get("wininet_proxy_enabled"),
        "wininet_proxy_server": proxy.get("wininet_proxy_server"),
        "winhttp_direct_access": proxy.get("winhttp_direct_access"),
        "localhost_port": proxy.get("localhost_port"),
        "listener_found": owner.get("listener_found"),
        "primary_classification": classification.get("primary_classification"),
    }
    ts = proxy.get("timestamp_utc") or utc_now_iso()
    for i, (signal, value) in enumerate(signals.items()):
        items.append(
            EvidenceItem(
                evidence_id=f"ev-{i}",
                event_id=incident_id,
                timestamp_utc=ts,
                source="evidence_case_builder",
                signal=signal,
                observed_value=str(value),
                tier=classification.get("evidence_tier", "OBSERVED_ONLY"),
            )
        )
    return items


def build_evidence_case_from_fixture(
    fixture_path: str | Path,
    *,
    title: str = "",
) -> EvidenceCase:
    """Materialize a full pipeline case from a portfolio case-study fixture."""
    path = Path(fixture_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return build_evidence_case_from_dict(data, fixture_source=str(path), title=title or data.get("title", ""))


def build_evidence_case_from_dict(
    data: dict[str, Any],
    *,
    fixture_source: str = "",
    title: str = "",
) -> EvidenceCase:
    case_id = data.get("case_id") or _new_id("case")
    incident_id = case_id
    created = utc_now_iso()
    classification = data.get("classification") or {}
    proof = data.get("proof") or {}
    policy_raw = data.get("policy_decision") or {}
    remediation = data.get("remediation_preview") or {}
    audit_raw = data.get("audit_trail") or {}

    observation = ObservationStage(
        observation_id=_new_id("obs"),
        timestamp_utc=created,
        source=audit_raw.get("source", "fixture"),
        symptom=data.get("symptom", ""),
        raw_signals={
            "proxy_state": data.get("proxy_state"),
            "proxy_owner": data.get("proxy_owner"),
            "classification": classification.get("primary_classification"),
        },
        limitations=list(classification.get("limitations") or _EPISTEMIC_LIMITATIONS[:2]),
    )

    items = _evidence_items_from_fixture(data, incident_id)
    tier = classification.get("evidence_tier", "OBSERVED_ONLY")
    bundle = EvidenceBundle(
        bundle_id=_new_id("bun"),
        incident_id=incident_id,
        created_at=created,
        tier=tier,
        items=items,
        summary=classification.get("primary_classification", ""),
    )
    evidence = EvidenceStage(
        bundle=bundle,
        tier_summary=f"Tier {tier}",
        limitations=list(classification.get("limitations") or []),
    )

    hyp = Hypothesis(
        hypothesis_id=_new_id("hyp"),
        event_id=incident_id,
        title=proof.get("hypothesis", classification.get("primary_classification", "Unknown")),
        explanation=proof.get("hypothesis", ""),
        confidence=float(classification.get("confidence") or proof.get("conclusion", {}).get("confidence") or 0.5),
        incident_type=classification.get("primary_classification", "UNKNOWN"),
    )
    hypothesis = HypothesisStage(
        hypothesis=hyp,
        alternatives=["Remote upstream failure", "DNS failure", "User error"],
        limitations=list(proof.get("limitations") or []),
    )

    attempts = [
        ValidationAttempt(
            name=str(a.get("name", "attempt")),
            status=_map_attempt_status(a.get("status")),
        )
        for a in proof.get("proof_attempts") or []
    ]
    validation = ValidationStage(
        validation_id=_new_id("val"),
        timestamp_utc=created,
        status=_map_validation_status(proof.get("conclusion", {}).get("status")),
        proof_level=classification.get("proof_level", "observed"),
        attempts=attempts,
        limitations=list(proof.get("limitations") or []),
    )

    risk = RiskAssessmentStage(
        assessment_id=_new_id("risk"),
        severity=(classification.get("severity") or "medium"),  # type: ignore[arg-type]
        confidence=float(classification.get("confidence") or 0.5),
        user_impact=data.get("symptom", ""),
        not_evidence_of=["Malware proof", "MITM proof"] if "MITM" in str(proof.get("limitations")) else [],
        limitations=list(classification.get("limitations") or []),
    )

    decision_obj = build_decision(
        bundle,
        hyp,
        recommended_action=policy_raw.get("action", "PREVIEW_ONLY"),
        risk_level=classification.get("severity", "medium"),
        requires_human_review=bool(policy_raw.get("requires_confirmation")),
    )
    policy = evaluate_policy(
        decision=decision_obj,
        bundle=bundle,
        requested_action=policy_raw.get("action", "PREVIEW_ONLY"),
        dry_run=bool(data.get("dry_run", policy_raw.get("dry_run", True))),
    )
    decision = DecisionStage(decision=decision_obj, policy=policy)

    dry_run = bool(remediation.get("dry_run", policy_raw.get("dry_run", True)))
    execution = ExecutionStage(
        execution_id=_new_id("exe"),
        timestamp_utc=created,
        action_id=policy_raw.get("action", ""),
        dry_run=dry_run,
        status="preview" if dry_run else "not_requested",
        registry_modified=False,
        confirmation_token=policy_raw.get("confirmation_token", "") if not dry_run else "",
        policy_outcome=policy_raw.get("outcome", policy.outcome),
        planned_changes=list(remediation.get("planned_changes") or []),
        limitations=["No registry values modified during evidence-case create."],
    )

    outcome = OutcomeStage(
        outcome=IncidentOutcome(
            outcome_id=_new_id("out"),
            decision_id=decision_obj.decision_id,
            incident_id=incident_id,
            created_at=created,
            recommended_action=decision_obj.recommended_action,
            policy_outcome=policy.outcome,
            actual_outcome="preview_only" if dry_run else "pending",
            was_blocked_by_policy=policy.outcome == "BLOCK",
            notes="Evidence case created from fixture — no live execution.",
        ),
        resolution_summary="Preview-only pipeline trace.",
    )

    audit_record = AuditRecord(
        audit_id=_new_id("aud"),
        timestamp_utc=created,
        action_type="evidence_attached",
        incident_id=incident_id,
        decision_id=decision_obj.decision_id,
        payload={
            "event_id": audit_raw.get("event_id"),
            "classification": audit_raw.get("classification"),
            "policy_decision": audit_raw.get("policy_decision"),
            "evidence_tier": audit_raw.get("evidence_tier"),
        },
    )
    audit = AuditStage(records=[audit_record])

    learning = LearningStage(
        records=[
            LearningRecord(
                record_id=_new_id("lrn"),
                decision_id=decision_obj.decision_id,
                created_at=created,
                feedback_type="case_created",
                metrics_snapshot={"confidence": hyp.confidence, "tier": tier},
            )
        ],
        recommended_controls=["NET-001 Proxy Baseline Validation"],
        recommended_tests=["proxy-status", "proxy-proof"],
    )

    return EvidenceCase(
        case_id=case_id,
        title=title or data.get("title", case_id),
        created_at=created,
        fixture_source=fixture_source,
        observation=observation,
        evidence=evidence,
        hypothesis=hypothesis,
        validation=validation,
        risk_assessment=risk,
        decision=decision,
        execution=execution,
        outcome=outcome,
        audit=audit,
        learning=learning,
        limitations=_EPISTEMIC_LIMITATIONS,
        tags=["fixture-built", classification.get("primary_classification", "")],
    )


def _map_attempt_status(status: str | None) -> str:
    mapping = {
        "supported": "passed",
        "passed": "passed",
        "failed": "failed",
        "skipped": "skipped",
        "inconclusive": "inconclusive",
    }
    return mapping.get(str(status or "").lower(), "inconclusive")  # type: ignore[return-value]


def _map_validation_status(status: str | None) -> str:
    mapping = {
        "supported": "passed",
        "proven": "passed",
        "failed": "failed",
        "inconclusive": "inconclusive",
    }
    return mapping.get(str(status or "").lower(), "not_run")  # type: ignore[return-value]


def save_evidence_case(case: EvidenceCase, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(case.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_evidence_case(path: str | Path) -> EvidenceCase:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EvidenceCase.model_validate(data)
