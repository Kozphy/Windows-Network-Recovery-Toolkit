"""Safety regression tests for telemetry package (diagnostic-only)."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.policy import OperatorContext, evaluate, is_shell_injection
from telemetry.audit import append_registry_writer_evidence_audit
from telemetry.registry_writer_fusion import default_no_telemetry_evidence


def test_telemetry_audit_row_excludes_raw_events_by_default(tmp_path: Path) -> None:
    evidence = default_no_telemetry_evidence()
    path = append_registry_writer_evidence_audit(
        evidence,
        audit_path=tmp_path / "registry_writer_evidence.jsonl",
    )
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert "matched_events" not in row
    assert row["evidence_level"] == "NO_TELEMETRY"


def test_high_risk_actions_remain_blocked() -> None:
    gate = evaluate({}, "process_kill_forbidden", OperatorContext(role="admin", surface="api"))
    assert gate.execute_allowed is False


def test_shell_injection_still_rejected() -> None:
    assert is_shell_injection("reset_dns; calc.exe") is True


def test_telemetry_cli_module_is_importable() -> None:
    from telemetry.cli import build_parser

    parser = build_parser()
    assert parser.prog == "telemetry.cli"
