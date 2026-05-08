"""Deterministic offline safety regressions — no repair subprocesses, bat scripts, registry, or network."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from platform_core.event_bus import read_events
from platform_core.events import ActorAttribution, AuditEvent, NormalizedEvent
from platform_core.policy import ACTION_REGISTRY, validate_confirmation_phrase
from platform_core.policy.engine import OperatorContext, evaluate
from platform_core.privacy import stable_endpoint_hash
from platform_core.remediation_registry import canonical_action_name, build_action_registry_legacy_dict
from platform_core.replay.runner import summarize_inline

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_policy_preview_operator_execute_denied_pending_admin() -> None:
    g = evaluate({}, "reset_dns", OperatorContext(role="operator", surface="api"))
    assert g.preview_allowed is True
    assert g.execute_allowed is False
    assert "operator_may_preview_only_live_requires_admin" in g.reason_codes


def test_policy_admin_eligible_but_confirmation_phrase_required() -> None:
    g = evaluate({}, "reset_proxy", OperatorContext(role="admin", surface="api"))
    assert g.preview_allowed and g.execute_allowed
    assert g.required_confirmation == "RUN_PROXY_RESET"
    assert "confirmation_phrase_required" in g.reason_codes


def test_proxy_reset_accepts_RUN_PROXY_RESET_not_RESTORE_PROXY_string() -> None:
    """Platform registry phrase is RUN_PROXY_RESET; RESTORE_PROXY is denied (distinct from rollback CLI phrases)."""

    assert validate_confirmation_phrase("reset_proxy", "RUN_PROXY_RESET")
    assert not validate_confirmation_phrase("reset_proxy", "RESTORE_PROXY")
    assert not validate_confirmation_phrase("reset_proxy", "RESTORE_WININET")


def test_firewall_manual_only_blocks_structured_execution() -> None:
    fw = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert fw.execute_allowed is False
    assert "manual_only_registry_entry" in fw.reason_codes


def test_arbitrary_command_alias_always_forbidden() -> None:
    assert canonical_action_name("arbitrary_command") == "arbitrary_command_forbidden"
    blocked = evaluate({}, "arbitrary_command", OperatorContext(role="admin", surface="api"))
    assert blocked.preview_allowed is False
    assert blocked.execute_allowed is False
    assert "arbitrary_commands_forbidden" in blocked.reason_codes


def test_unknown_action_default_deny() -> None:
    g = evaluate({}, "not_a_real_action_ever", OperatorContext(role="admin", surface="api"))
    assert g.preview_allowed is False and g.execute_allowed is False
    assert "unknown_action" in g.reason_codes


def test_arbitrary_shell_flag_is_always_denied_even_if_hypothetical() -> None:
    g = evaluate(
        {},
        "reset_dns",
        OperatorContext(role="admin", surface="api"),
        allow_arbitrary_shell=True,
    )
    assert g.preview_allowed is False and g.execute_allowed is False
    assert "arbitrary_shell_forbidden_even_if_requested" in g.reason_codes


def test_event_bus_skips_bad_jsonl_lines(tmp_path: Path) -> None:
    fx = ("b" * 32,)
    junk = '{"broken":}'
    ok_line = json.dumps(
        {
            "schema_version": "1",
            "event_id": "e-safe",
            "event_type": "x",
            "severity": "low",
            "endpoint_id_hash": fx[0],
            "signals": {"remediation_action": "inspect_proxy"},
        },
    )
    p = tmp_path / "mixed.jsonl"
    p.write_text(f"{junk}\n{ok_line}\n", encoding="utf-8")
    good, errs = read_events(p)
    assert len(good) == 1 and len(errs) == 1


def test_stable_endpoint_hash_is_hex_digest_without_plaintext_hostname() -> None:
    hn = "hr-contoso-warehouse-042.internal"
    digest = stable_endpoint_hash(hn, os_version="10")
    assert len(digest) == 32 and all(c in "0123456789abcdef" for c in digest)
    assert hn.lower() not in digest.lower()
    assert "contoso" not in digest.lower()


def test_normalized_event_rejects_non_hex_endpoint_identity() -> None:
    with pytest.raises(ValidationError):
        NormalizedEvent(
            schema_version="1",
            event_id="p1",
            event_type="t",
            endpoint_id_hash="not-a-hash-or-ip-192.168.1.1!!!!",
            signals={},
        )


def test_normalized_event_blocks_proof_claim_without_evidentiary_source() -> None:
    with pytest.raises(ValidationError):
        NormalizedEvent(
            schema_version="1",
            event_id="p2",
            event_type="t",
            endpoint_id_hash="ab" + "cd" * 15,
            signals={},
            actor_attribution=ActorAttribution(confidence="proof", provider="none", details={}),
        )


def test_audit_row_symmetric_proof_validation() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(
            audit_id="a1",
            event_id="e1",
            endpoint_id_hash="ef" + "01" * 15,
            actor_attribution=ActorAttribution(
                confidence="proof",
                provider="windows_stub",
                details={"tamper_evident_source": ""},
            ),
        )


def test_replay_summarize_inline_does_not_open_filesystems(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[tuple[str, str]] = []

    def _spy_open(path, mode: str = "r", *a, **k):  # type: ignore[no-untyped-def]
        opened.append((str(path), mode))
        raise AssertionError(f"replay inline must not open({path}, {mode})")

    monkeypatch.setattr(Path, "open", _spy_open)
    summarize_inline(
        [
            {
                "schema_version": "1",
                "signals": {"remediation_action": "inspect_proxy"},
                "policy_decision": {
                    "execute_allowed": False,
                    "preview_allowed": True,
                    "reason_codes": ["ok"],
                    "required_role": "admin",
                    "required_confirmation": None,
                    "risk_tier": "read_only",
                },
            },
        ],
    )
    assert opened == [], opened


def test_replay_detects_drifting_embedded_execute_gate() -> None:
    stale = {
        "execute_allowed": False,
        "preview_allowed": True,
        "reason_codes": ["stale_preview_only"],
        "required_role": "admin",
        "required_confirmation": "RUN_PROXY_RESET",
        "risk_tier": "medium",
    }
    rec = {
        "schema_version": "1",
        "signals": {"remediation_action": "reset_proxy", "simulated_operator_role": "admin"},
        "policy_decision": stale,
    }
    s = summarize_inline([rec])
    assert s.changed_decisions == 1 and s.newly_allowed_preview == 0


def test_remediation_aliases_share_legacy_action_registry_meta() -> None:
    flat = build_action_registry_legacy_dict()
    canon = ACTION_REGISTRY["firewall_reset_manual_only"]
    assert ACTION_REGISTRY["reset_firewall"] == canon
    assert flat["reset_firewall"] == canon
    assert flat["firewall_reset_manual_only"] == canon
    assert flat["arbitrary_command"] == flat["arbitrary_command_forbidden"]


def test_attribution_process_heuristic_never_claims_proof() -> None:
    from platform_core.attribution.polling import PollingHeuristicProvider

    p = PollingHeuristicProvider()
    out = p.attribute({"process_names_sample": ["something-clash-something.exe"]})
    assert out.confidence != "proof"
    assert "Heuristic" in " ".join(out.notes)


def test_smoke_python_m_src_fixture_diagnose_isolated_repo(tmp_path: Path) -> None:
    iso = tmp_path / "isolate_root"
    fixture = _REPO_ROOT / "tests" / "fixtures" / "features_healthy_signals.json"
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "src",
            "--repo-root",
            str(iso),
            "diagnose",
            "--fixture",
            str(fixture),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    assert r.returncode == 0, (r.stderr, r.stdout)
    assert (iso / "reports" / "last_diagnosis.json").is_file()
    audit = iso / "logs" / "decision_audit.jsonl"
    assert audit.is_file()


def test_smoke_failure_system_help_exits_clean() -> None:
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
    r = subprocess.run(
        [sys.executable, "-m", "failure_system", "--help"],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    assert r.returncode == 0
