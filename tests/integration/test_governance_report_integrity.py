"""Governance report integrity when audit chain valid vs missing."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.governance.chain_of_custody import verify_chain

ROOT = Path(__file__).resolve().parents[2]


def test_chained_audit_sample_verifies() -> None:
    path = ROOT / "tests/fixtures/risk_analytics/audit_sample_chained/incidents.jsonl"
    records = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok, msg = verify_chain(records)
    assert ok, msg


def test_sample_governance_report_has_limitations() -> None:
    text = (ROOT / "reports/sample_governance_report.md").read_text(encoding="utf-8").lower()
    assert "limitations" in text
    assert "management information" in text
    assert "preview-only" in text or "preview" in text
