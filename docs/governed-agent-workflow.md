# Governed Agent Investigation Workflow

This module provides a narrow orchestration boundary for agent-assisted incident investigation.
It is deliberately **explanation-first** and **non-executing**.

## Trust boundary

```text
Incident
  -> evidence collection
  -> deterministic classification
  -> agent explanation
  -> optional remediation preview
  -> mandatory human review
```

The orchestrator does not accept an execution callback. This prevents an LLM or agent from
turning a recommendation into an authorized mutation. Remediation remains preview-only and
must pass the repository's existing policy and typed-confirmation controls outside this layer.

## Decisions

- `EXPLAIN_ONLY`: evidence and classification are returned without a remediation preview.
- `HUMAN_REVIEW_REQUIRED`: a preview exists, but execution remains unauthorized.
- `BLOCKED`: policy or classification blocked the path; no preview is emitted.

## Minimal example

```python
from src.platform_core.agent import GovernedInvestigation

workflow = GovernedInvestigation(
    collect_evidence=collect_evidence,
    classify=classify_evidence,
    explain=explain_for_operator,
    preview_remediation=build_preview,
)

result = workflow.run(
    {"endpoint": "host-001"},
    request_remediation_preview=True,
)

assert result.execution_authorized is False
```

## Verification

```bash
pytest tests/platform_core/agent/test_governed_investigation.py -q
```

This is a portfolio-grade foundation, not a claim of autonomous remediation or production AI safety certification.
