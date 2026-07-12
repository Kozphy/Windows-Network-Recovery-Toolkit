"""Level 1 custody + tip anchor tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.platform_core.audit.custody import append_custody_event, map_event_to_action
from src.platform_core.audit.paths import tip_path_for
from src.platform_core.audit.tip_anchor import verify_audit_with_tip, write_tip_anchor
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain


def test_map_event_to_action() -> None:
    assert map_event_to_action("guardian_preview") == "remediation_previewed"
    assert map_event_to_action("proxy_fix_applied") == "action_executed"
    assert map_event_to_action("unknown_event") == "event_received"


def test_append_audit_writes_tip_anchor(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "custody.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    tip = tip_path_for(path)
    assert tip.is_file()
    data = json.loads(tip.read_text(encoding="utf-8"))
    assert data["tip_hash"] == r1.current_hash
    assert data["record_count"] == 1
    r2 = append_audit("action_executed", incident_id="i1", path=path)
    data2 = json.loads(tip.read_text(encoding="utf-8"))
    assert data2["tip_hash"] == r2.current_hash
    assert data2["record_count"] == 2


def test_verify_audit_with_tip_detects_mismatch(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "custody.jsonl"
    append_audit("event_received", path=path)
    append_audit("policy_evaluated", path=path)
    tip = tip_path_for(path)
    ok = verify_audit_with_tip(path, tip_path=tip)
    assert ok["verified"] is True
    assert ok["tip_match"] is True

    # Forge tip to wrong hash while leaving JSONL alone
    write_tip_anchor(tip_hash="deadbeef", record_count=2, audit_path=path, tip_path=tip)
    bad = verify_audit_with_tip(path, tip_path=tip)
    assert bad["chain_verified"] is True
    assert bad["tip_match"] is False
    assert bad["verified"] is False


def test_verify_require_tip_fails_when_missing(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "custody.jsonl"
    append_audit("event_received", path=path, write_tip=False)
    result = verify_audit_with_tip(path, require_tip=True)
    assert result["tip_present"] is False
    assert result["verified"] is False


def test_rewritten_chain_mismatches_old_tip(tmp_path: Path) -> None:
    """Full file rewrite can keep internal chain valid but tip will not match."""
    reset_chain_for_tests()
    path = tmp_path / "custody.jsonl"
    append_audit("event_received", path=path, payload={"a": 1})
    tip = tip_path_for(path)
    old_tip = json.loads(tip.read_text(encoding="utf-8"))

    # Replace file with a new valid chain (different content)
    reset_chain_for_tests()
    path.write_text("", encoding="utf-8")
    append_audit("event_received", path=path, payload={"forged": True}, write_tip=False)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chain_ok, _ = verify_chain(records)
    assert chain_ok is True
    # Restore old tip (attacker forgot to update external tip)
    tip.write_text(json.dumps(old_tip), encoding="utf-8")
    result = verify_audit_with_tip(path, tip_path=tip)
    assert result["chain_verified"] is True
    assert result["tip_match"] is False
    assert result["verified"] is False


def test_append_custody_event_tolerates_append_audit_without_write_tip(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: soft-fail path must not raise when writer rejects write_tip."""
    from src.platform_core.audit import custody as custody_mod

    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))

    def _legacy_append(action_type, *, actor="platform", payload=None, path=None):
        return type(
            "Rec",
            (),
            {
                "audit_id": "x",
                "action_type": action_type,
                "current_hash": "abc",
            },
        )()

    monkeypatch.setattr(
        "src.platform_core.audit.writer.append_audit",
        _legacy_append,
    )
    out = custody_mod.append_custody_event(
        "ensure_proxy_health",
        dry_run=True,
        path=tmp_path / "c.jsonl",
        soft_fail=True,
    )
    assert out["ok"] is True, out
    assert out["current_hash"] == "abc"


def test_append_custody_event_scrubs_confirm_keys(tmp_path: Path, monkeypatch) -> None:
    reset_chain_for_tests()
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    path = tmp_path / "canonical_custody.jsonl"
    out = append_custody_event(
        "proxy_fix_applied",
        confirmation_supplied=True,
        extra={"confirm": "DISABLE_WININET_PROXY", "reason": "ok"},
        path=path,
    )
    assert out["ok"] is True
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert "confirm" not in row["payload"].get("detail", {})
    assert row["payload"]["detail"]["reason"] == "ok"
    assert row["payload"]["confirmation_supplied"] is True


def test_guardian_dual_writes_custody(tmp_path: Path, monkeypatch) -> None:
    from src.proxy_drift.guardian import run_dead_proxy_guardian_once

    reset_chain_for_tests()
    monkeypatch.setenv("WNT_AUDIT_DIR", str(tmp_path))
    legacy = tmp_path / "proxy_guardian.jsonl"

    class _Reg:
        proxy_enable = 0
        proxy_server = None
        auto_config_url = None

    with (
        patch("src.proxy_drift.guardian.read_proxy_registry", return_value=_Reg()),
        patch("src.proxy_drift.guardian.parse_proxy_server") as parsed,
        patch(
            "src.proxy_drift.guardian.classify_proxy_drift",
            return_value={"classification": "NO_PROXY", "limitations": []},
        ),
    ):
        parsed.return_value.is_localhost_proxy = False
        parsed.return_value.localhost_port = None
        parsed.return_value.raw = None
        result = run_dead_proxy_guardian_once(dry_run=True, audit_path=legacy)

    assert result["action_taken"] == "none"
    assert legacy.is_file()
    custody = tmp_path / "canonical_custody.jsonl"
    assert custody.is_file()
    tip = tip_path_for(custody)
    assert tip.is_file()
    verify = verify_audit_with_tip(custody)
    assert verify["verified"] is True
