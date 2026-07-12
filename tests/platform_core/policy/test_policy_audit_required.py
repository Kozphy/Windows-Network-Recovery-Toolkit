"""Policy evaluation requires audit trail in pipeline."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.audit.writer import reset_chain_for_tests
from src.platform_core.pipeline import run_decision_pipeline


def test_pipeline_writes_audit(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reset_chain_for_tests()
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    result = run_decision_pipeline(signals={"wininet_proxy_enabled": True})
    assert len(result.audit_ids) >= 4
    custody = tmp_path / "canonical_custody.jsonl"
    assert custody.is_file()
    assert sum(1 for line in custody.read_text(encoding="utf-8").splitlines() if line.strip()) >= 4
