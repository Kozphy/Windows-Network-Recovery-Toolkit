"""Final causation engine — fixture scenarios for proxy forensics."""

from __future__ import annotations

from pathlib import Path

from src.proxy_guard.final_causation import collect_final_causation
from src.proxy_guard.registry_writer_proof import collect_registry_writer_evidence
from src.reports.proxy_causation_report import render_final_causation_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "proxy_causation"


def _run_scenario(name: str):
    fixture_dir = FIXTURES / name
    return collect_final_causation(
        repo_root=Path.cwd(),
        fixture_dir=fixture_dir,
        since_minutes=30,
    )


def test_scenario1_proven_writer_and_port_owner() -> None:
    report = _run_scenario("scenario1_proven_writer_port_owner")
    assert report.verdict == "PROVEN_PROXY_WRITER_AND_PORT_OWNER"
    assert report.proof_level in ("FINAL_CAUSATION", "PROVEN_REGISTRY_WRITER")
    assert "node.exe" in report.root_cause_sentence.lower()
    chain = (report.evidence_tree.get("process_tree") or {}).get("chain") or []
    assert any("powershell" in str(n.get("image", "")).lower() for n in chain)


def test_scenario2_likely_local_proxy_tool() -> None:
    report = _run_scenario("scenario2_likely_local_tool")
    assert report.verdict == "LIKELY_LOCAL_PROXY_TOOL"
    assert report.proven_vs_likely["registry_writer"] == "not observed"


def test_scenario3_tool_conflict_flapping() -> None:
    report = _run_scenario("scenario3_tool_conflict")
    assert report.verdict == "TOOL_CONFLICT_PROXY_FLAPPING"


def test_scenario4_suspicious_unknown() -> None:
    report = _run_scenario("scenario4_suspicious_unknown")
    assert report.verdict == "SUSPICIOUS_UNKNOWN_PROXY"
    assert report.evidence_tree.get("path_proof", {}).get("failure_mode") == "proxy_broken"


def test_scenario5_inconclusive() -> None:
    report = _run_scenario("scenario5_inconclusive")
    assert report.verdict == "INCONCLUSIVE"


def test_registry_writer_proof_from_fixture() -> None:
    path = FIXTURES / "scenario1_proven_writer_port_owner" / "sysmon.json"
    rows = collect_registry_writer_evidence(fixture_path=path)
    assert len(rows) >= 1
    assert rows[0].proof_level == "PROVEN"
    assert rows[0].event_id == 13


def test_markdown_report_sections() -> None:
    report = _run_scenario("scenario1_proven_writer_port_owner")
    md = render_final_causation_markdown(report)
    for section in (
        "## A. Executive Summary",
        "## H. Final Verdict",
        "## I. What is proven vs what is only likely",
        "Observation is not proof",
    ):
        assert section in md


def test_sysmon_upgrades_proof_level() -> None:
    without = _run_scenario("scenario2_likely_local_tool")
    with_proof = _run_scenario("scenario1_proven_writer_port_owner")
    assert without.proof_level in ("OBSERVED_ONLY", "CORRELATED")
    assert with_proof.proof_level in ("PROVEN_REGISTRY_WRITER", "FINAL_CAUSATION")
