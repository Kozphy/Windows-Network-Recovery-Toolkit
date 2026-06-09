"""Unified platform replay determinism."""

from __future__ import annotations

from pathlib import Path

from src.platform.registry import get_adapter
from src.platform.replay import replay_all, run_pipeline


def test_replay_fingerprint_stable(tmp_path: Path) -> None:
    adapter = get_adapter("windows")
    audit = tmp_path / "audit.jsonl"
    r1 = run_pipeline(adapter, fixture_name="proxy_localhost.json", audit_path=audit)
    r2 = run_pipeline(adapter, fixture_name="proxy_localhost.json", audit_path=audit, record_audit=False)
    assert r1.fingerprint == r2.fingerprint


def test_replay_all_domains() -> None:
    results = replay_all()
    assert len(results) == 16
    assert len({r.fingerprint for r in results}) == len(results)
