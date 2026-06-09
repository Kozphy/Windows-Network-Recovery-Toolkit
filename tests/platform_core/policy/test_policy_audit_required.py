"""Policy evaluation requires audit trail in pipeline."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.audit.writer import reset_chain_for_tests
from src.platform_core.pipeline import run_decision_pipeline


def test_pipeline_writes_audit(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reset_chain_for_tests()
    import src.platform_core.audit.writer as aw

    monkeypatch.setattr(aw, "_DEFAULT_PATH", tmp_path / "audit.jsonl")
    result = run_decision_pipeline(signals={"wininet_proxy_enabled": True})
    assert len(result.audit_ids) >= 4
