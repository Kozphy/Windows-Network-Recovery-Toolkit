from __future__ import annotations

from pathlib import Path

from agent.executor import RepairExecutor
from agent.planner import plan
from agent.schemas import DiagnosticEvidence, RankedCause, RepairStep


def test_executor_blocks_firewall_without_dual_confirm() -> None:
    repo = Path(__file__).resolve().parents[1]
    evidence = DiagnosticEvidence.from_dict(
        {
            "ping_ok": True,
            "dns_ok": True,
            "tcp_443_ok": True,
            "https_ok": False,
            "winhttp_proxy_summary": "",
            "user_proxy_enabled": False,
            "user_proxy_server": None,
            "tls_cert_issue_detected": False,
            "firewall_blocking_suspected": True,
            "time_wait_count": 0,
            "established_count": 0,
            "recent_processes": [],
            "notes": "",
        },
    )
    primary = RankedCause(
        category="firewall_issue",
        confidence=0.9,
        explanation="test",
    )
    p = plan(primary, evidence)
    ex = RepairExecutor(repo, confirm_firewall=False, confirmed_scripts=frozenset())
    for step in p.steps:
        ok, reason = ex.should_run(step)
        if "reset_firewall" in step.script_relative_path.lower():
            assert ok is False
            assert "firewall" in reason.lower()


def test_executor_confirmed_script_matches_across_path_separators() -> None:
    repo = Path(__file__).resolve().parents[1]
    step = RepairStep(
        script_relative_path=r"scripts\reset_firewall.bat",
        description="test",
        risk="HIGH",
        requires_confirmation=True,
        destructive=True,
    )
    ex = RepairExecutor(
        repo,
        confirm_firewall=True,
        confirmed_scripts=frozenset({"scripts/reset_firewall.bat"}),
    )
    ok, reason = ex.should_run(step)
    assert ok is True, reason
