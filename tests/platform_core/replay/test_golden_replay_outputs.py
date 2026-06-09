"""Golden replay outputs."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.replay.certifier import certify_case

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "platform_core" / "golden" / "proxy_drift.jsonl"


def test_golden_proxy_drift() -> None:
    cert = certify_case(jsonl_path=GOLDEN)
    assert cert.certification_hash
    assert cert.tier in {"OBSERVED_ONLY", "CORRELATED_PROCESS", "PATH_VALIDATED", "PROVEN_REGISTRY_WRITER", "FINAL_CAUSATION"}
