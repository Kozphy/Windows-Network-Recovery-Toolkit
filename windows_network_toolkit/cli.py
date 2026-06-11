"""CLI for ``python -m toolkit`` and ``python -m windows_network_toolkit``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from windows_network_toolkit.audit.replay import replay_to_dict
from windows_network_toolkit.audit.report_generator import generate_erp_report, generate_report


def _resolve_fixture(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_file():
        return path
    repo = Path(__file__).resolve().parents[1]
    for candidate in (
        repo / "windows_network_toolkit" / "examples" / path_str,
        repo / "tests" / "fixtures" / "enert" / path_str,
        repo / "tests" / "fixtures" / "enert" / f"{path_str}.json",
    ):
        if candidate.is_file():
            return candidate
    return path


def cmd_replay(args: argparse.Namespace) -> int:
    path = _resolve_fixture(args.fixture)
    if not path.is_file():
        print(f"Fixture not found: {args.fixture}", file=sys.stderr)
        return 1
    payload = replay_to_dict(path, dry_run=True)
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(generate_report(
            timeline=payload["timeline"],
            decision=payload["decision"],
            policy=payload["policy"],
            remediation=payload["remediation"],
            audit_rows=[payload.get("audit") or {}],
            fmt="markdown",
        ))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    if args.fixture:
        path = _resolve_fixture(args.fixture)
        if not path.is_file():
            print(f"Fixture not found: {args.fixture}", file=sys.stderr)
            return 1
        payload = replay_to_dict(path, dry_run=True)
        text = generate_report(
            timeline=payload["timeline"],
            decision=payload["decision"],
            policy=payload["policy"],
            remediation=payload["remediation"],
            audit_rows=[payload.get("audit") or {}],
            fmt=args.format,  # type: ignore[arg-type]
        )
    elif args.url:
        from windows_network_toolkit.diagnostics.proxy import run_full_incident_report

        package = run_full_incident_report(args.url)
        text = generate_erp_report(package, fmt=args.format)  # type: ignore[arg-type]
    else:
        print("Provide fixture path or --url for live diagnostic report.", file=sys.stderr)
        return 1
    print(text)
    return 0


def cmd_replay_certify(args: argparse.Namespace) -> int:
    from src.platform_core.replay.certifier import certify_case

    path = _resolve_fixture(args.fixture)
    cert = certify_case(jsonl_path=path)
    print(json.dumps({
        "certified": cert.certified,
        "certification_hash": cert.certification_hash,
        "tier": cert.tier,
        "policy_outcome": cert.policy_outcome,
        "errors": cert.errors,
    }, indent=2))
    return 0 if cert.certified else 1


def cmd_bad_gateway_diagnose(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.bad_gateway import run_bad_gateway_diagnose

    report = run_bad_gateway_diagnose(args.url, dry_run=True)
    if args.json_only:
        print(json.dumps(report, indent=2))
    else:
        print(f"=== {report['headline']} ===")
        print(f"Classification: {report['classification']} (confidence {report['confidence']:.2f})")
        print(f"Recommended: {report['recommended_action']}")
        print(f"Policy: {report['policy_gate'].get('outcome')}")
        for note in report.get("safety_notes", []):
            print(f"  • {note}")
        if not args.summary_only:
            print(json.dumps(report, indent=2))
    return 0


def cmd_proxy_status(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.proxy import run_proxy_status

    payload = run_proxy_status()
    print(json.dumps(payload, indent=2))
    return 0


def cmd_proxy_attribution(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.proxy import run_proxy_attribution

    payload = run_proxy_attribution()
    print(json.dumps(payload, indent=2))
    return 0


def cmd_proxy_writer_attribution(args: argparse.Namespace) -> int:
    from src.platform_core.attribution.writer_engine import run_proxy_writer_attribution

    inject = None
    inject_sysmon = None
    if args.fixture:
        path = _resolve_fixture(args.fixture)
        data = json.loads(path.read_text(encoding="utf-8"))
        inject = data.get("writer_attribution")
        inject_sysmon = data.get("sysmon_events")
    payload = run_proxy_writer_attribution(inject=inject, inject_sysmon=inject_sysmon)
    print(json.dumps(payload.to_dict(), indent=2))
    return 0


def cmd_tls_proof(args: argparse.Namespace) -> int:
    from src.platform_core.tls import run_tls_proof

    inject = None
    inject_roots = None
    if args.fixture:
        path = _resolve_fixture(args.fixture)
        data = json.loads(path.read_text(encoding="utf-8"))
        inject = data.get("tls_proof")
        inject_roots = data.get("root_store")
    payload = run_tls_proof(args.url, inject=inject, inject_roots=inject_roots)
    print(json.dumps(payload.to_dict(), indent=2))
    return 0


def cmd_website_risk(args: argparse.Namespace) -> int:
    from src.platform_core.website_risk import run_website_risk

    inject = None
    if args.fixture:
        path = _resolve_fixture(args.fixture)
        data = json.loads(path.read_text(encoding="utf-8"))
        inject = data.get("website_risk")
    payload = run_website_risk(args.url, inject=inject)
    print(json.dumps(payload.to_dict(), indent=2))
    return 0


def cmd_evidence_report(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.evidence import run_evidence_assessment
    from src.platform_core.evidence_report import generate_evidence_report

    inject_writer = inject_proof = inject_tls = inject_website = inject_sysmon = None
    if args.fixture:
        path = _resolve_fixture(args.fixture)
        data = json.loads(path.read_text(encoding="utf-8"))
        inject_writer = data.get("writer_attribution")
        inject_proof = data.get("proof_results")
        inject_tls = data.get("tls_proof")
        inject_website = data.get("website_risk")
        inject_sysmon = data.get("sysmon_events")

    package = run_evidence_assessment(
        args.url,
        inject_writer=inject_writer,
        inject_proof=inject_proof,
        inject_tls=inject_tls,
        inject_website=inject_website,
        inject_sysmon=inject_sysmon,
    )
    text = generate_evidence_report(package, fmt=args.format)  # type: ignore[arg-type]
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return 0


def cmd_proxy_proof(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.proxy import run_proxy_proof

    payload = run_proxy_proof(args.url)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_proxy_timeline(args: argparse.Namespace) -> int:
    from windows_network_toolkit.diagnostics.proxy import run_proxy_timeline

    payload = run_proxy_timeline(args.url or None)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_audit_verify(args: argparse.Namespace) -> int:
    from src.platform_core.governance.chain_of_custody import verify_chain

    path = Path(args.audit_file)
    if not path.is_file():
        print(f"Audit file not found: {path}", file=sys.stderr)
        return 1
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    ok, msg = verify_chain(records)
    print(json.dumps({"verified": ok, "message": msg, "records": len(records)}, indent=2))
    return 0 if ok else 1


def cmd_demo(args: argparse.Namespace) -> int:
    repo = Path(__file__).resolve().parents[1]
    fixture = repo / "windows_network_toolkit" / "examples" / "proxy_drift_incident.jsonl"
    payload = replay_to_dict(fixture, dry_run=True)
    print("=== Endpoint Reliability Golden Demo ===")
    print(f"Fixture: {fixture.name}")
    print(f"Incident type: {payload['decision'].get('incident_type')}")
    print(f"Policy: {payload['policy'].get('outcome')}")
    print()
    print(generate_report(
        timeline=payload["timeline"],
        decision=payload["decision"],
        policy=payload["policy"],
        remediation=payload["remediation"],
        audit_rows=[payload.get("audit") or {}],
        fmt="markdown",
    ))
    print()
    print("Dashboard: http://127.0.0.1:8000/dashboard/  (run: make demo-api)")
    return 0


def main(argv: list[str] | None = None, *, prog: str = "toolkit") -> int:
    parser = argparse.ArgumentParser(prog=prog, description="Endpoint Reliability Decision Platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay", help="Replay a JSONL incident fixture")
    replay.add_argument("fixture", help="Path to JSONL fixture")
    replay.add_argument("--format", choices=["json", "markdown"], default="markdown")
    replay.add_argument("--out", default="", help="Optional JSON output path")
    replay.set_defaults(func=cmd_replay)

    report = sub.add_parser("report", help="Generate audit report from fixture or live URL")
    report.add_argument("fixture", nargs="?", default="", help="Path to JSONL fixture")
    report.add_argument("--url", default="", help="Live diagnostic URL (uses proxy pipeline)")
    report.add_argument("--format", choices=["json", "markdown", "html"], default="markdown")
    report.set_defaults(func=cmd_report)

    certify = sub.add_parser("replay-certify", help="Certify deterministic replay")
    certify.add_argument("fixture", help="Path to JSONL fixture")
    certify.set_defaults(func=cmd_replay_certify)

    bg = sub.add_parser("bad-gateway-diagnose", help="Diagnose 502/bad-gateway (read-only)")
    bg.add_argument("--url", required=True, help="Target HTTPS URL")
    bg.add_argument("--json-only", action="store_true", help="Emit JSON only")
    bg.add_argument("--summary-only", action="store_true", help="Human summary without full JSON")
    bg.set_defaults(func=cmd_bad_gateway_diagnose)

    ps = sub.add_parser("proxy-status", help="Read-only WinINET/WinHTTP proxy status")
    ps.set_defaults(func=cmd_proxy_status)

    pa = sub.add_parser("proxy-attribution", help="Read-only proxy listener attribution")
    pa.set_defaults(func=cmd_proxy_attribution)

    pwa = sub.add_parser(
        "proxy-writer-attribution",
        help="Proxy registry writer attribution with Sysmon E13 fusion (read-only)",
    )
    pwa.add_argument("--fixture", default="", help="Optional fixture JSON for replay")
    pwa.set_defaults(func=cmd_proxy_writer_attribution)

    tls = sub.add_parser("tls-proof", help="TLS certificate contrast direct vs proxied path (read-only)")
    tls.add_argument("--url", required=True, help="Target HTTPS URL")
    tls.add_argument("--fixture", default="", help="Optional fixture JSON for replay")
    tls.set_defaults(func=cmd_tls_proof)

    wr = sub.add_parser("website-risk", help="Website risk heuristic scoring (read-only)")
    wr.add_argument("--url", required=True, help="Target URL")
    wr.add_argument("--fixture", default="", help="Optional fixture JSON for replay")
    wr.set_defaults(func=cmd_website_risk)

    er = sub.add_parser(
        "evidence-report",
        help="Merged evidence timeline report (JSONL/Markdown/HTML, preview-only)",
    )
    er.add_argument("--url", required=True, help="Target URL for network proof")
    er.add_argument("--fixture", default="", help="Optional fixture JSON for replay")
    er.add_argument("--format", choices=["json", "jsonl", "markdown", "html"], default="markdown")
    er.add_argument("--out", default="", help="Optional output file path")
    er.set_defaults(func=cmd_evidence_report)

    pp = sub.add_parser("proxy-proof", help="Direct vs proxied path proof (read-only)")
    pp.add_argument("--url", required=True, help="Target HTTPS URL")
    pp.set_defaults(func=cmd_proxy_proof)

    pt = sub.add_parser("proxy-timeline", help="Build incident timeline from proxy state")
    pt.add_argument("--url", default="", help="Optional URL for proof probes")
    pt.set_defaults(func=cmd_proxy_timeline)

    audit = sub.add_parser("audit", help="Audit chain operations")
    audit_sub = audit.add_subparsers(dest="audit_cmd", required=True)
    verify = audit_sub.add_parser("verify", help="Verify hash chain integrity")
    verify.add_argument("audit_file", help="Path to audit JSONL")
    verify.set_defaults(func=cmd_audit_verify)

    demo = sub.add_parser("demo", help="Golden fixture demo (read-only)")
    demo.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
