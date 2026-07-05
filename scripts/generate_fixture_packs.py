"""Generate demo fixture packs and chained audit sample."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIXTURES = {
    "dead_proxy_config": ("examples/evidence/DEAD_PROXY_CONFIG.json", "DEAD_PROXY_CONFIG", "T2", "PREVIEW"),
    "wininet_winhttp_mismatch": (
        "examples/evidence/WININET_WINHTTP_MISMATCH.json",
        "WININET_WINHTTP_MISMATCH",
        "T2",
        "PREVIEW",
    ),
    "reverter_suspected": (
        "examples/evidence/REVERTER_SUSPECTED.json",
        "REVERTER_SUSPECTED",
        "T2",
        "REQUIRE_HUMAN_REVIEW",
    ),
    "suspicious_proxy": (
        "fixtures/proxy/suspicious-remote-proxy.json",
        "SUSPICIOUS_PROXY",
        "T2",
        "REQUIRE_HUMAN_REVIEW",
    ),
    "tls_path_mismatch": (
        "examples/evidence/POSSIBLE_MITM_RISK.json",
        "POSSIBLE_MITM_RISK",
        "T3",
        "REQUIRE_HUMAN_REVIEW",
    ),
    "pac_configured": (
        "tests/fixtures/proxy_transitions/pac_added.json",
        "PAC_CONFIGURED",
        "T1",
        "ALLOW",
    ),
}


def main() -> None:
    for name, (src_rel, primary, tier, gate) in FIXTURES.items():
        d = ROOT / "fixtures" / name
        d.mkdir(parents=True, exist_ok=True)
        src = ROOT / src_rel
        raw = json.loads(src.read_text(encoding="utf-8"))
        if "proxy_state" not in raw and "before" in raw:
            raw = {
                "schema_version": "portfolio_evidence.v1",
                "incident_id": f"FIX-{name.upper()}",
                "proxy_state": raw.get("after") or raw.get("before"),
                "classification": {
                    "primary_classification": primary,
                    "limitations": ["Fixture pack for demo replay."],
                },
            }
        (d / "raw_signals.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
        cls = raw.get("classification") or {}
        expected_cls = {
            "primary_classification": cls.get("primary_classification", primary),
            "secondary_signals": cls.get("secondary_signals", []),
            "proof_tier": tier,
            "confidence_min": 0.3,
            "limitations_required": True,
        }
        (d / "expected_classification.json").write_text(
            json.dumps(expected_cls, indent=2), encoding="utf-8"
        )
        pol = raw.get("policy_decision") or {}
        expected_pol = {
            "policy_gate": gate,
            "outcome": pol.get("outcome", gate),
            "dry_run_default": True,
            "destructive_actions_blocked": True,
        }
        (d / "expected_policy.json").write_text(json.dumps(expected_pol, indent=2), encoding="utf-8")
        report = (
            f"# Expected Report — {name}\n\n"
            f"Classification: `{expected_cls['primary_classification']}` · "
            f"Proof tier: {tier} · Gate: {gate}\n\n"
            "See [reports/sample_governance_report.md](../../reports/sample_governance_report.md).\n\n"
            "## Limitations\n\n"
            "- Demo fixture — not live endpoint evidence\n"
            "- Does not prove malware or MITM confirmation\n"
        )
        (d / "expected_report.md").write_text(report, encoding="utf-8")

    from src.platform_core.audit.writer import append_audit, reset_chain_for_tests

    audit_dir = ROOT / "tests/fixtures/risk_analytics/audit_sample_chained"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "incidents.jsonl"
    if path.exists():
        path.unlink()
    reset_chain_for_tests()
    append_audit(
        "event_received",
        incident_id="DEMO-59081",
        path=path,
        payload={"classification": "DEAD_PROXY_CONFIG"},
    )
    append_audit(
        "policy_evaluated",
        incident_id="DEMO-59081",
        path=path,
        payload={"gate": "PREVIEW_ONLY"},
    )
    append_audit(
        "remediation_previewed",
        incident_id="DEMO-59081",
        path=path,
        payload={"action": "disable_wininet_proxy", "dry_run": True},
    )


if __name__ == "__main__":
    main()
