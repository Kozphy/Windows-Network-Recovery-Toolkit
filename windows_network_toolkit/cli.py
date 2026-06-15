"""CLI for ``python -m toolkit`` and ``python -m windows_network_toolkit``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from windows_network_toolkit.audit.replay import replay_to_dict
from windows_network_toolkit.audit.report_generator import generate_erp_report, generate_report


def _emit_json(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _load_fixture_data(path_str: str) -> dict:
    path = _resolve_fixture(path_str)
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_fixture(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_file():
        return path
    repo = Path(__file__).resolve().parents[1]
    for candidate in (
        repo / "windows_network_toolkit" / "examples" / path_str,
        repo / "tests" / "fixtures" / "enert" / path_str,
        repo / "tests" / "fixtures" / "enert" / f"{path_str}.json",
        repo / "tests" / "fixtures" / "classification" / path_str,
        repo / "tests" / "fixtures" / "classification" / f"{path_str}.json",
        repo / "tests" / "fixtures" / "url_diagnostics" / path_str,
        repo / "tests" / "fixtures" / "url_diagnostics" / f"{path_str}.json",
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

    inject = None
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject = data
    payload = run_proxy_status(inject=inject)
    _emit_json(payload)
    return 0


def cmd_proxy_owner(args: argparse.Namespace) -> int:
    from windows_network_toolkit.proxy_owner import detect_proxy_owner

    inject = None
    if args.fixture:
        inject = _load_fixture_data(args.fixture).get("proxy_owner") or _load_fixture_data(args.fixture)
    payload = detect_proxy_owner(inject=inject)
    _emit_json(payload)
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    from windows_network_toolkit.proof import enrich_diagnose_payload, run_diagnose_proof

    inject = None
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject = data.get("proof") or data
    payload = run_diagnose_proof(args.url or None, inject=inject)
    out = payload.to_dict()
    if getattr(args, "principles", False):
        out = enrich_diagnose_payload(out, include_principles=True)
    _emit_json(out)
    return 0


def cmd_principles_explain(_args: argparse.Namespace) -> int:
    from src.platform_core.principles.validator import explain_principles

    _emit_json(explain_principles())
    return 0


def cmd_principles_validate(args: argparse.Namespace) -> int:
    from src.platform_core.principles.validator import validate_fixture_path

    path = args.fixture
    if not path:
        repo = Path(__file__).resolve().parents[1]
        path = str(repo / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json")
    result = validate_fixture_path(path)
    _emit_json(result.to_dict())
    return 0 if result.compliant else 1


def cmd_proxy_disable(args: argparse.Namespace) -> int:
    from windows_network_toolkit.proxy_remediation import run_proxy_disable

    dry_run = args.dry_run.lower() != "false"
    payload = run_proxy_disable(dry_run=dry_run, confirm=args.confirm or "")
    _emit_json(payload)
    if payload.get("unsupported_platform"):
        return 2
    if not dry_run and not payload.get("action_allowed"):
        return 1
    return 0


def cmd_proxy_watch(args: argparse.Namespace) -> int:
    from windows_network_toolkit.watch import run_proxy_watch

    inject_sequence = None
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject_sequence = data.get("watch_sequence")
    payload = run_proxy_watch(
        duration=int(args.duration),
        interval=float(args.interval),
        inject_sequence=inject_sequence,
    )
    _emit_json(payload)
    return 0 if not payload.get("unsupported_platform") else 2


def cmd_proxy_report(args: argparse.Namespace) -> int:
    from windows_network_toolkit.report import build_proxy_report

    inject = None
    if args.fixture:
        inject = _load_fixture_data(args.fixture).get("report") or _load_fixture_data(args.fixture)
    payload = build_proxy_report(
        url=args.url or None,
        inject=inject,
        include_principles=bool(getattr(args, "include_principles", False)),
    )
    _emit_json(payload)
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
    from windows_network_toolkit.timeline import build_proxy_timeline

    if args.audit_only:
        payload = build_proxy_timeline()
    else:
        payload = run_proxy_timeline(args.url or None, use_audit=bool(args.audit))
    _emit_json(payload)
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


def cmd_fleet_simulate(args: argparse.Namespace) -> int:
    from windows_network_toolkit.fleet import cmd_fleet_simulate as _run

    return _run(args)


def cmd_risk_analytics(args: argparse.Namespace) -> int:
    from src.platform_core.risk_platform.pipeline import (
        executive_summary_markdown,
        load_case_fixture,
        run_risk_analytics_pipeline,
    )

    fixture = load_case_fixture(args.fixture)
    result = run_risk_analytics_pipeline(fixture)
    if args.format == "markdown":
        print(executive_summary_markdown(result))
    else:
        print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_url_diagnose(args: argparse.Namespace) -> int:
    from windows_network_toolkit.url_diagnose import diagnose_url, explain_report

    inject = None
    body_text = ""
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject = data.get("inject") or data
        body_text = str(data.get("body_text") or (inject or {}).get("body_text") or "")

    report = diagnose_url(
        args.url,
        domain_profile=args.domain_profile,
        follow_redirects=bool(args.follow_redirects),
        max_redirects=int(args.max_redirects),
        compare_browser=bool(args.compare_browser),
        user_agent=args.user_agent or "",
        timeout=float(args.timeout),
        no_body=bool(args.no_body),
        classify_soft_404=bool(args.classify_soft_404),
        save_evidence=bool(args.save_evidence),
        evidence_dir=args.evidence_dir,
        inject=inject,
        body_text=body_text,
    )
    if args.explain:
        print(explain_report(report))
    else:
        _emit_json(report)
    return 0


def cmd_evidence_case(args: argparse.Namespace) -> int:
    from windows_network_toolkit.evidence_case_cli import (
        create_case,
        export_schema,
        report_case,
        validate_case_file,
    )

    sub = args.evidence_case_cmd
    if sub == "create":
        fixture = _resolve_fixture(args.fixture)
        if not fixture.is_file():
            print(f"Fixture not found: {args.fixture}", file=sys.stderr)
            return 1
        payload = create_case(fixture=str(fixture), out=args.out, title=args.title or "")
        if args.json:
            _emit_json(payload)
        else:
            print(json.dumps({"case_id": payload["case_id"], "out": args.out}, indent=2))
        return 0
    if sub == "report":
        text = report_case(args.case_file, fmt=args.format)
        print(text)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        return 0
    if sub == "validate":
        result = validate_case_file(args.case_file)
        _emit_json(result)
        return 0 if result.get("valid") else 1
    if sub == "schema":
        payload = export_schema(args.out)
        if args.json:
            _emit_json({"schema_path": payload["schema_path"]})
        else:
            print(json.dumps({"schema_path": payload["schema_path"]}, indent=2))
        return 0
    print("Unknown evidence-case subcommand", file=sys.stderr)
    return 1


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
    ps.add_argument("--fixture", default="", help="Optional fixture JSON")
    ps.set_defaults(func=cmd_proxy_status)

    po = sub.add_parser("proxy-owner", help="Detect localhost proxy listener process (JSON)")
    po.add_argument("--fixture", default="", help="Optional fixture JSON")
    po.set_defaults(func=cmd_proxy_owner)

    pd = sub.add_parser("proxy-disable", help="Preview/apply safe HKCU WinINET proxy disable")
    pd.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        help="Preview only (default). Pass false to apply: --dry-run false",
    )
    pd.add_argument("--confirm", default="", help="Typed confirmation token")
    pd.set_defaults(func=cmd_proxy_disable)

    pw = sub.add_parser("proxy-watch", help="Poll WinINET proxy for drift (read-only)")
    pw.add_argument("--duration", default="900", help="Watch duration seconds")
    pw.add_argument("--interval", default="2", help="Poll interval seconds")
    pw.add_argument("--fixture", default="", help="Optional fixture JSON")
    pw.set_defaults(func=cmd_proxy_watch)

    prpt = sub.add_parser("proxy-report", help="Structured incident-style JSON report")
    prpt.add_argument("--url", default="", help="Optional URL for proof section")
    prpt.add_argument("--fixture", default="", help="Optional fixture JSON")
    prpt.add_argument(
        "--include-principles",
        action="store_true",
        help="Include evidence chain, principle compliance, and safe remediation sections",
    )
    prpt.set_defaults(func=cmd_proxy_report)

    principles = sub.add_parser("principles", help="Epistemic principle contracts")
    principles_sub = principles.add_subparsers(dest="principles_cmd", required=True)
    p_explain = principles_sub.add_parser("explain", help="List the four epistemic principles")
    p_explain.set_defaults(func=cmd_principles_explain)
    p_validate = principles_sub.add_parser("validate", help="Validate fixture against principles")
    p_validate.add_argument(
        "--fixture",
        default="",
        help="Fixture JSON path (default: case_studies/cs1_wininet_proxy_drift/fixture.json)",
    )
    p_validate.set_defaults(func=cmd_principles_validate)

    diag = sub.add_parser("diagnose", help="Structured proof diagnosis")
    diag.add_argument("--proof", action="store_true", help="Run proof envelope")
    diag.add_argument(
        "--principles",
        action="store_true",
        help="Include principle compliance sections in output",
    )
    diag.add_argument("--url", default="", help="Optional URL for network probes")
    diag.add_argument("--fixture", default="", help="Optional fixture JSON")
    diag.set_defaults(func=cmd_diagnose)

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

    pt = sub.add_parser("proxy-timeline", help="Build incident timeline from proxy state or audit")
    pt.add_argument("--url", default="", help="Optional URL for proof probes")
    pt.add_argument("--audit", action="store_true", help="Prefer .audit/ timeline when available")
    pt.add_argument("--audit-only", action="store_true", help="Read .audit/ only")
    pt.set_defaults(func=cmd_proxy_timeline)

    audit = sub.add_parser("audit", help="Audit chain operations")
    audit_sub = audit.add_subparsers(dest="audit_cmd", required=True)
    verify = audit_sub.add_parser("verify", help="Verify hash chain integrity")
    verify.add_argument("audit_file", help="Path to audit JSONL")
    verify.set_defaults(func=cmd_audit_verify)

    demo = sub.add_parser("demo", help="Golden fixture demo (read-only)")
    demo.set_defaults(func=cmd_demo)

    fs = sub.add_parser(
        "fleet-simulate",
        help="Fleet simulation summary from JSONL fixture (read-only)",
    )
    fs.add_argument(
        "--fixture",
        default="tests/fixtures/fleet/fleet_100_endpoints.jsonl",
        help="Fleet JSONL fixture path",
    )
    fs.add_argument("--format", choices=["json", "markdown"], default="json")
    fs.set_defaults(func=cmd_fleet_simulate)

    ra = sub.add_parser(
        "risk-analytics",
        help="Technology Risk & Control Analytics assessment (fixture-safe)",
    )
    ra.add_argument(
        "--fixture",
        default="tests/fixtures/case_studies/case_1_dead_wininet_proxy.json",
    )
    ra.add_argument("--format", choices=["json", "markdown"], default="json")
    ra.set_defaults(func=cmd_risk_analytics)

    ud = sub.add_parser(
        "url-diagnose",
        help="Distinguish network failure from application/content-layer URL issues (read-only)",
    )
    ud.add_argument("--url", required=True, help="Target URL to diagnose")
    ud.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON (default)")
    ud.add_argument("--fixture", default="", help="Optional fixture JSON with inject probes")
    ud.add_argument("--follow-redirects", dest="follow_redirects", action="store_true", default=True)
    ud.add_argument("--no-follow-redirects", dest="follow_redirects", action="store_false")
    ud.add_argument("--max-redirects", default="10")
    ud.add_argument("--compare-browser", action="store_true")
    ud.add_argument("--user-agent", default="")
    ud.add_argument("--timeout", default="10")
    ud.add_argument("--no-body", action="store_true")
    ud.add_argument("--save-evidence", action="store_true")
    ud.add_argument("--evidence-dir", default="./evidence")
    ud.add_argument("--classify-soft-404", dest="classify_soft_404", action="store_true", default=True)
    ud.add_argument("--no-classify-soft-404", dest="classify_soft_404", action="store_false")
    ud.add_argument("--domain-profile", default="generic", choices=["generic", "linkedin"])
    ud.add_argument("--explain", action="store_true", help="Human-readable summary (JSON still via default)")
    ud.set_defaults(func=cmd_url_diagnose)

    ec = sub.add_parser(
        "evidence-case",
        help="Evidence Case pipeline model (create / report / validate / schema)",
    )
    ec_sub = ec.add_subparsers(dest="evidence_case_cmd", required=True)

    ec_create = ec_sub.add_parser("create", help="Build case JSON from fixture (read-only)")
    ec_create.add_argument(
        "--fixture",
        default="tests/fixtures/case_studies/case_1_dead_wininet_proxy.json",
    )
    ec_create.add_argument("--out", required=True, help="Output case JSON path")
    ec_create.add_argument("--title", default="", help="Optional case title override")
    ec_create.add_argument("--json", action="store_true", help="Emit full case JSON to stdout")
    ec_create.set_defaults(func=cmd_evidence_case)

    ec_report = ec_sub.add_parser("report", help="Render case report")
    ec_report.add_argument("case_file", help="Path to evidence case JSON")
    ec_report.add_argument("--format", choices=["json", "markdown"], default="markdown")
    ec_report.add_argument("--out", default="", help="Optional output file")
    ec_report.set_defaults(func=cmd_evidence_case)

    ec_validate = ec_sub.add_parser("validate", help="Validate case structure and safety")
    ec_validate.add_argument("case_file", help="Path to evidence case JSON")
    ec_validate.set_defaults(func=cmd_evidence_case)

    ec_schema = ec_sub.add_parser("schema", help="Export JSON Schema for EvidenceCase")
    ec_schema.add_argument("--out", default="schemas/evidence_case.schema.json")
    ec_schema.add_argument("--json", action="store_true")
    ec_schema.set_defaults(func=cmd_evidence_case)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
