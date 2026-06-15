"""Evidence Case report generation."""

from __future__ import annotations

from typing import Literal

from .models import EvidenceCase

ReportFormat = Literal["json", "markdown"]


def generate_case_report(case: EvidenceCase, *, fmt: ReportFormat = "markdown") -> str:
    if fmt == "json":
        import json

        return json.dumps(case.to_dict(), indent=2, ensure_ascii=False)
    return _markdown_report(case)


def _markdown_report(case: EvidenceCase) -> str:
    lines = [
        f"# Evidence Case: {case.title}",
        "",
        f"**Case ID:** `{case.case_id}`  ",
        f"**Schema:** `{case.schema_version}`  ",
        f"**Created:** {case.created_at}  ",
        "",
        f"> {case.epistemic_notice}",
        "",
        "## Pipeline",
        "",
        "| Stage | Summary |",
        "|-------|---------|",
        f"| Observation | {case.observation.symptom or 'signals captured'} |",
        f"| Evidence | Tier `{case.evidence.bundle.tier}` · {len(case.evidence.bundle.items)} items |",
        f"| Hypothesis | {case.hypothesis.hypothesis.title} (`{case.hypothesis.hypothesis.incident_type}`) |",
        f"| Validation | `{case.validation.status}` · {case.validation.proof_level} |",
        f"| Risk Assessment | `{case.risk_assessment.severity}` · confidence {case.risk_assessment.confidence:.2f} |",
        f"| Decision | `{case.decision.decision.recommended_action}` |",
        f"| Execution | `{case.execution.status}` · dry_run={case.execution.dry_run} |",
        f"| Outcome | {case.outcome.resolution_summary or 'pending'} |",
        f"| Audit | {len(case.audit.records)} record(s) |",
        f"| Learning | {len(case.learning.records)} record(s) |",
        "",
        "## Observation",
        "",
        f"- Source: `{case.observation.source}`",
        f"- Symptom: {case.observation.symptom}",
        "",
        "## Hypothesis",
        "",
        case.hypothesis.hypothesis.explanation or "_No explanation provided._",
        "",
        "## Decision & policy",
        "",
        f"- Recommended action: `{case.decision.decision.recommended_action}`",
    ]
    if case.decision.policy:
        lines.append(f"- Policy outcome: `{case.decision.policy.outcome}`")
    lines.extend(
        [
            "",
            "## Execution (preview contract)",
            "",
            f"- Registry modified: **{case.execution.registry_modified}**",
            f"- Confirmation token: `{case.execution.confirmation_token or 'none'}`",
            "",
            "## Limitations",
            "",
        ]
    )
    for lim in case.limitations:
        lines.append(f"- {lim}")
    return "\n".join(lines)
