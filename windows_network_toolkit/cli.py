"""CLI entrypoint for ``python -m windows_network_toolkit`` and ``python -m toolkit``.

Module responsibility:
    Parse subcommands and delegate to library modules. All JSON output uses UTF-8 and
    ``ensure_ascii=False`` for operator readability.

System placement:
    Top-level operator interface for evidence collection, analytics, governance reports,
    and gated remediation preview/apply. Business logic lives in sibling modules — this
    file wires argparse only.

Key invariants:
    * ``proxy-disable`` defaults to ``--dry-run true`` (preview only).
    * Read-only commands: ``proxy-status``, ``proxy-health``, ``proxy-watch``, analytics-*.
    * Fixture resolution searches ``tests/fixtures/`` and ``windows_network_toolkit/examples/``.

Side effects:
    Varies by subcommand — see individual ``cmd_*`` handlers. Mutating paths:
    ``proxy-disable`` (registry when dry-run false + typed confirm), optional ``--out`` writes.

Failure modes:
    Exit code 1 for validation/confirmation failures; 2 for unsupported platform (non-Windows
    remediation). Fixture not found prints to stderr and returns 1.

Audit Notes:
    * Prefer ``proxy-disable --dry-run`` before live apply; confirm token required for apply.
    * Analytics and evidence commands are read-only — safe for portfolio demos on fixtures.

Engineering Notes:
    Subcommand handlers stay thin to preserve testability of underlying modules and to avoid
    duplicating policy logic already enforced in ``proxy_remediation`` and ``safety``.

See also: ``docs/ONBOARDING.md`` and ``docs/code-documentation-standards.md``.
"""

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
        repo / "tests" / "fixtures" / "case_studies" / path_str,
        repo / "tests" / "fixtures" / "case_studies" / f"{path_str}.json",
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
    """Emit read-only WinINET/WinHTTP proxy status JSON.

    Args:
        args: Namespace with optional ``fixture`` for offline state injection.

    Returns:
        0 on success.

    Side effects:
        Read-only registry/netsh when no fixture; prints JSON to stdout.
    """
    from windows_network_toolkit.diagnostics.proxy import run_proxy_status

    inject = None
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject = data
    payload = run_proxy_status(inject=inject)
    _emit_json(payload)
    return 0


def cmd_proxy_owner(args: argparse.Namespace) -> int:
    """Emit localhost proxy listener process attribution JSON.

    Args:
        args: Namespace with optional ``fixture`` for inject envelope.

    Returns:
        0 on success.

    Side effects:
        Read-only port/process resolution when no fixture.

    Notes:
        Listener process is correlation only — not registry writer proof.
    """
    from windows_network_toolkit.proxy_owner import detect_proxy_owner

    inject = None
    if args.fixture:
        inject = _load_fixture_data(args.fixture).get("proxy_owner") or _load_fixture_data(args.fixture)
    payload = detect_proxy_owner(inject=inject)
    _emit_json(payload)
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Emit structured proof diagnosis JSON for a URL or fixture.

    Args:
        args: Namespace with ``url``, optional ``fixture``, optional ``principles`` flag.

    Returns:
        0 on success.

    Side effects:
        Read-only network/registry evidence collection when not using fixture.
    """
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
    """Run gated WinINET proxy disable (preview by default).

    Args:
        args: Namespace with ``dry_run`` (default true) and ``confirm`` token.

    Returns:
        0 on preview success or allowed apply; 1 when apply blocked; 2 on non-Windows.

    Side effects:
        When ``dry_run`` is false and confirmation matches, mutates HKCU WinINET registry
        via ``run_proxy_disable`` and appends ``proxy-disable.jsonl`` audit rows.

    Audit Notes:
        Live apply requires typed confirmation phrase — never bypass via CLI flags alone.
    """
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
    """Poll WinINET proxy for drift; append changes to proxy-watch JSONL.

    Args:
        args: ``duration``, ``interval``, ``coalesce_ms``, ``fixture``, format flags.

    Returns:
        0 on success; 2 when platform unsupported without fixture.

    Side effects:
        Appends ``.audit/proxy-watch.jsonl``; runs health probes on localhost transitions.

    Audit Notes:
        Read-only on registry — no auto-disable. Reverter flags require human review.
    """
    from windows_network_toolkit.watch import format_proxy_change_human, run_proxy_watch

    inject_sequence = None
    health_inject = None
    if args.fixture:
        data = _load_fixture_data(args.fixture)
        inject_sequence = data.get("watch_sequence")
        health_inject = data.get("health_inject")
    payload = run_proxy_watch(
        duration=int(args.duration),
        interval=float(args.interval),
        coalesce_ms=int(args.coalesce_ms),
        inject_sequence=inject_sequence,
        health_inject=health_inject,
        run_direct_probe=not args.no_direct_probe,
        run_proxy_probe=not args.no_proxy_probe,
        timeout_seconds=float(args.timeout),
    )
    if payload.get("unsupported_platform"):
        _emit_json(payload)
        return 2
    if args.format == "human":
        changes = [e for e in payload.get("events", []) if e.get("event") == "proxy_change"]
        if not changes:
            print("No proxy changes detected during watch window.")
        for ch in changes:
            print(format_proxy_change_human(ch))
            print()
        if args.json_also:
            _emit_json(payload)
    else:
        _emit_json(payload)
    return 0


def cmd_proxy_replay(args: argparse.Namespace) -> int:
    """Replay proxy-watch JSONL through state machine and control tests.

    Args:
        args: ``input`` JSONL path, ``coalesce_ms``, ``format`` (json|human).

    Returns:
        0 on success.

    Side effects:
        Read-only — no host mutation.
    """
    from windows_network_toolkit.proxy_replay import replay_proxy_file

    payload = replay_proxy_file(
        args.input,
        coalesce_ms=int(args.coalesce_ms),
    )
    if args.format == "human":
        summary = payload.get("summary") or {}
        print(f"Replay: {summary.get('input_event_count', 0)} input rows -> {summary.get('coalesced_event_count', 0)} classified events")
        for ev in payload.get("events") or []:
            print(json.dumps(ev, indent=2))
            print()
        for ctrl in payload.get("controls") or []:
            print(f"{ctrl.get('control_id')}: {ctrl.get('status')}")
        if args.json_also:
            _emit_json(payload)
    else:
        _emit_json(payload)
    return 0


def cmd_proxy_health(args: argparse.Namespace) -> int:
    """Run localhost proxy health probes and emit human or JSON audit payload.

    Args:
        args: Supports ``--fixture``, ``--json``, probe toggles, and optional ``--host``/``--port``.

    Returns:
        0 always on successful probe run (health failure is data, not CLI error).

    Side effects:
        Network probes when not using fixture inject; read-only on registry.
    """
    from windows_network_toolkit.proxy_health import (
        build_proxy_health_audit_payload,
        check_localhost_proxy_health,
        classify_incident_from_health,
        format_proxy_health_human,
        run_proxy_health_for_state,
    )
    from windows_network_toolkit.proxy_owner import detect_proxy_owner
    from windows_network_toolkit.proxy_state import collect_proxy_state_model

    fixture_data: dict = {}
    inject_state = None
    health_inject = None
    owner_inject = None
    if args.fixture:
        fixture_data = _load_fixture_data(args.fixture)
        inject_state = fixture_data.get("proxy_state") or fixture_data
        health_inject = fixture_data.get("health_inject")
        owner_inject = fixture_data.get("proxy_owner")

    state = collect_proxy_state_model(inject=inject_state).to_dict()
    urls = list(args.url) if args.url else None
    health_kwargs: dict = {
        "test_urls": urls,
        "timeout_seconds": float(args.timeout),
        "run_direct_probe": not args.no_direct_probe,
        "run_proxy_probe": not args.no_proxy_probe,
        "inject": health_inject,
    }

    if args.host and args.port:
        owner_payload = owner_inject or detect_proxy_owner(inject_state=inject_state)
        health = check_localhost_proxy_health(
            args.host,
            int(args.port),
            listener_info=owner_payload,
            **{k: v for k, v in health_kwargs.items() if v is not None},
        )
        classification = classify_incident_from_health(health, wininet_enabled=True)
        payload = build_proxy_health_audit_payload(
            wininet=state,
            health=health,
            classification=classification,
        )
    else:
        owner_payload = detect_proxy_owner(inject=owner_inject, inject_state=inject_state)
        payload = run_proxy_health_for_state(state, owner_payload, **health_kwargs)

    if args.json:
        _emit_json(payload)
    else:
        print(format_proxy_health_human(payload))
        if args.json_also:
            print()
            _emit_json(payload)
    return 0


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
    """Emit read-only proxy listener attribution JSON.

    Args:
        args: No fixture — live collection only.

    Returns:
        0 on success.

    Side effects:
        Read-only process/port correlation.
    """
    from windows_network_toolkit.diagnostics.proxy import run_proxy_attribution

    payload = run_proxy_attribution()
    print(json.dumps(payload, indent=2))
    return 0


def cmd_proxy_writer_attribution(args: argparse.Namespace) -> int:
    """Emit registry writer attribution with optional Sysmon fixture inject.

    Args:
        args: Optional ``fixture`` with ``writer_attribution`` and ``sysmon_events``.

    Returns:
        0 on success.

    Side effects:
        May read EventLog/Sysmon when live; fixture mode is read-only.

    Notes:
        Writer proof requires telemetry — absence is not proof of benign intent.
    """
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
    """Contrast TLS certificate paths direct vs proxied (read-only).

    Args:
        args: ``url`` and optional ``fixture`` with ``tls_proof`` / ``root_store``.

    Returns:
        0 on success.

    Side effects:
        HTTPS handshakes when live — no registry mutation.

    Notes:
        Path mismatch supports triage — not confirmed MITM or malware.
    """
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
    """Generate evidence report (latest proxy package, analytics, or URL assessment).

    Args:
        args: ``--latest`` for proxy-path package; ``--analytics`` for pipeline report;
            ``--url`` for full evidence assessment; optional ``fixture`` and ``--out``.

    Returns:
        0 on success; 1 when required ``--url`` missing for non-latest mode.

    Side effects:
        Read-only evidence collection; optional write to ``--out`` path.

    Notes:
        Reports include ``limitations[]`` — management information, not audit opinions.
    """
    if getattr(args, "latest", False):
        from windows_network_toolkit.latest_evidence_report import (
            build_latest_evidence_package,
            render_latest_evidence_markdown,
        )

        inject_state = inject_owner = inject_health = inject_timeline = inject_reverter = None
        if args.fixture:
            data = _load_fixture_data(args.fixture)
            inject_state = data.get("proxy_state") or data
            inject_owner = data.get("proxy_owner")
            inject_health = data.get("health_inject")
            inject_timeline = data.get("timeline")
            inject_reverter = data.get("reverter_diagnosis")
        package = build_latest_evidence_package(
            inject_state=inject_state,
            inject_owner=inject_owner,
            inject_health=inject_health,
            inject_timeline=inject_timeline,
            inject_reverter=inject_reverter,
            health_kwargs={
                "run_direct_probe": not getattr(args, "no_direct_probe", False),
                "run_proxy_probe": not getattr(args, "no_proxy_probe", False),
            },
        )
        if args.format == "json":
            _emit_json(package)
        else:
            text = render_latest_evidence_markdown(package)
            print(text)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            content = (
                json.dumps(package, indent=2)
                if args.format == "json"
                else render_latest_evidence_markdown(package)
            )
            out.write_text(content, encoding="utf-8")
        return 0

    if getattr(args, "analytics", False):
        from windows_network_toolkit.analytics_pipeline import (
            render_analytics_evidence_report,
            run_endpoint_analytics_pipeline,
        )

        fixture = None
        if args.fixture:
            fixture = _load_fixture_data(args.fixture)
        payload = run_endpoint_analytics_pipeline(fixture=fixture)
        print(render_analytics_evidence_report(payload))
        if args.out:
            Path(args.out).write_text(render_analytics_evidence_report(payload), encoding="utf-8")
        return 0

    from src.platform_core.evidence_report import generate_evidence_report
    from windows_network_toolkit.diagnostics.evidence import run_evidence_assessment

    if not args.url:
        print("Provide --url or use --latest for proxy-path evidence report.", file=sys.stderr)
        return 1

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
    """Emit direct vs proxied path proof JSON for a URL (read-only).

    Args:
        args: Target ``url``.

    Returns:
        0 on success.

    Side effects:
        Network probes only — no registry mutation.
    """
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
    """Verify hash chain integrity of an audit JSONL file.

    Args:
        args: ``audit_file`` path to JSONL records.

    Returns:
        0 when chain verifies; 1 when file missing or chain invalid.

    Side effects:
        Read-only file read.

    Audit Notes:
        Chain integrity proves append-only consistency — not truth of observations.
    """
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


def cmd_risk_assess(args: argparse.Namespace) -> int:
    from src.platform_core.risk import assess_risk, load_fixture

    fixture = load_fixture(_resolve_fixture(args.fixture))
    _emit_json(assess_risk(fixture))
    return 0


def cmd_control_test(args: argparse.Namespace) -> int:
    from src.platform_core.risk import load_fixture, run_control_tests
    from src.platform_core.risk.control_test_mature import run_mature_control_tests

    fixture = load_fixture(_resolve_fixture(args.fixture))
    tests = run_control_tests(fixture)
    mature = run_mature_control_tests(fixture)
    _emit_json({
        "schema_version": "technology_risk_decision.v1",
        "command": "control-test",
        "case_id": fixture.get("case_id"),
        "control_tests": [t.model_dump() for t in tests],
        "mature_control_tests": [t.model_dump() for t in mature],
    })
    return 0


def cmd_governance_report(args: argparse.Namespace) -> int:
    from src.platform_core.governance.audit_report import build_audit_governance_report
    from src.platform_core.risk import build_governance_report, load_fixture

    if getattr(args, "audit_dir", None):
        audit_dir = Path(args.audit_dir)
        result = build_audit_governance_report(
            audit_dir,
            risk_register_path=Path(args.risk_register) if getattr(args, "risk_register", None) else None,
            format=args.format,
        )
        if args.format in ("markdown", "html"):
            print(result)
        else:
            _emit_json(result)
        return 0

    if not getattr(args, "fixture", None):
        print("governance-report requires --fixture or --audit-dir", file=sys.stderr)
        return 2

    fixture = load_fixture(_resolve_fixture(args.fixture))
    result = build_governance_report(fixture, format=args.format if args.format != "html" else "markdown")
    if args.format == "markdown":
        print(result)
    elif args.format == "html":
        from src.platform_core.governance.audit_report import _markdown_to_html

        print(_markdown_to_html(str(result)))
    else:
        _emit_json(result)
    return 0


def cmd_risk_kpi_summary(args: argparse.Namespace) -> int:
    from src.platform_core.analytics import build_risk_kpi_summary, format_risk_kpi_markdown

    audit_dir = Path(args.audit_dir)
    payload = build_risk_kpi_summary(audit_dir)
    if args.format == "markdown":
        print(format_risk_kpi_markdown(payload))
    else:
        _emit_json(payload)
    return 0


def cmd_powerbi_export(args: argparse.Namespace) -> int:
    from src.platform_core.analytics.powerbi_star_export import export_powerbi_star_schema

    audit_dir = Path(args.audit_dir)
    out_dir = Path(args.out_dir)
    payload = export_powerbi_star_schema(
        audit_dir,
        out_dir,
        include_seed=not getattr(args, "no_seed", False),
    )
    _emit_json(payload)
    return 0


def cmd_analytics_export_powerbi(args: argparse.Namespace) -> int:
    from src.platform_core.analytics.powerbi_export import (
        export_powerbi_from_audit,
        write_portfolio_sample,
    )

    out_dir = Path(args.out_dir)
    if getattr(args, "portfolio_sample", False):
        counts = write_portfolio_sample(out_dir)
        _emit_json(
            {
                "schema_version": "powerbi_export.v1",
                "command": "analytics-export-powerbi",
                "mode": "portfolio_sample",
                "out_dir": str(out_dir.resolve()),
                "record_counts": counts,
            }
        )
        return 0

    audit_dir = Path(args.audit_dir)
    payload = export_powerbi_from_audit(
        audit_dir,
        out_dir,
        include_portfolio_seed=bool(getattr(args, "include_seed", False)),
    )
    _emit_json(payload)
    return 0


def cmd_analytics_summary(args: argparse.Namespace) -> int:
    if getattr(args, "legacy_platform", False):
        from src.platform_core.analytics import build_analytics_summary, format_analytics_markdown

        audit_dir = Path(args.audit_dir)
        payload = build_analytics_summary(audit_dir)
        if args.format == "markdown":
            print(format_analytics_markdown(payload))
        else:
            _emit_json(payload)
        return 0

    from windows_network_toolkit.analytics_pipeline import (
        format_endpoint_analytics_summary_human,
        render_analytics_evidence_report,
        run_endpoint_analytics_pipeline,
    )

    fixture = None
    if args.fixture:
        fixture = _load_fixture_data(args.fixture)
    input_path = Path(args.input) if getattr(args, "input", "") else None
    payload = run_endpoint_analytics_pipeline(
        input_path=input_path,
        fixture=fixture,
        bucket=getattr(args, "bucket", "day") or "day",
        limit_processes=int(getattr(args, "limit_processes", 10) or 10),
    )
    if getattr(args, "json", False) or args.format == "json":
        _emit_json(payload)
    elif args.format == "markdown":
        print(render_analytics_evidence_report(payload))
    else:
        print(format_endpoint_analytics_summary_human(payload))
    return 0


def cmd_analytics_export(args: argparse.Namespace) -> int:
    from windows_network_toolkit.analytics_pipeline import (
        export_endpoint_analytics,
        run_endpoint_analytics_pipeline,
    )

    fixture = None
    if args.fixture:
        fixture = _load_fixture_data(args.fixture)
    input_path = Path(args.input) if args.input else None
    payload = run_endpoint_analytics_pipeline(
        input_path=input_path,
        fixture=fixture,
        bucket=args.bucket,
        limit_processes=int(args.limit_processes),
    )
    out_dir = Path(args.out)
    paths = export_endpoint_analytics(
        payload,
        out_dir,
        export_csv=args.format in ("csv", "both"),
    )
    _emit_json({"schema_version": "endpoint_evidence_analytics.v1", "out_dir": str(out_dir.resolve()), "files": paths})
    return 0


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


def cmd_reviewer_demo(args: argparse.Namespace) -> int:
    from windows_network_toolkit.reviewer_demo import run_reviewer_demo

    out_dir = Path(args.out) if args.out else None
    result = run_reviewer_demo(mode=args.mode, out_dir=out_dir)
    if args.json:
        _emit_json(result)
    return 0


def cmd_fleet_simulate(args: argparse.Namespace) -> int:
    from windows_network_toolkit.fleet_simulate import run_fleet_simulate

    summary = run_fleet_simulate(
        scenario=args.scenario,
        endpoints=int(args.endpoints),
        seed=int(args.seed),
        out_dir=Path(args.out),
    )
    _emit_json(summary)
    return 0


def main(argv: list[str] | None = None, *, prog: str = "toolkit") -> int:
    """Parse CLI arguments and dispatch to the selected subcommand handler.

    Args:
        argv: Argument vector; defaults to ``sys.argv[1:]``.
        prog: Program name shown in help text.

    Returns:
        Integer exit code from the invoked ``cmd_*`` handler.

    Side effects:
        Depends on subcommand — see handler docstrings. No side effects at parse time.

    Example:
        ``python -m windows_network_toolkit proxy-health --fixture tests/fixtures/proxy_health_dead.json --json``
    """
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
    pw.add_argument("--format", choices=("json", "human"), default="json", help="Output format")
    pw.add_argument("--json-also", action="store_true", help="With --format human, also emit JSON")
    pw.add_argument("--timeout", default="5", help="Health probe timeout seconds")
    pw.add_argument("--no-direct-probe", action="store_true", help="Skip direct HTTPS probes")
    pw.add_argument("--no-proxy-probe", action="store_true", help="Skip proxy forwarding probes")
    pw.add_argument(
        "--coalesce-ms",
        default="1000",
        help="Merge rapid registry sub-events within this window (200-5000 ms)",
    )
    pw.set_defaults(func=cmd_proxy_watch)

    preplay = sub.add_parser("proxy-replay", help="Replay proxy-watch JSONL through state machine")
    preplay.add_argument("--input", required=True, help="JSONL fixture or audit log path")
    preplay.add_argument(
        "--coalesce-ms",
        default="1000",
        help="Coalescing window in milliseconds (200-5000)",
    )
    preplay.add_argument("--format", choices=("json", "human"), default="json", help="Output format")
    preplay.add_argument("--json-also", action="store_true", help="With --format human, also emit JSON")
    preplay.set_defaults(func=cmd_proxy_replay)

    ph = sub.add_parser("proxy-health", help="Localhost proxy health check (read-only)")
    ph.add_argument("--host", default="", help="Override localhost host")
    ph.add_argument("--port", default="", help="Override localhost port")
    ph.add_argument("--url", action="append", default=[], help="Test URL (repeatable)")
    ph.add_argument("--timeout", default="5", help="Probe timeout seconds")
    ph.add_argument("--json", action="store_true", help="Emit JSON only")
    ph.add_argument("--json-also", action="store_true", help="Emit JSON after summary")
    ph.add_argument("--fixture", default="", help="Optional fixture JSON")
    ph.add_argument("--no-direct-probe", action="store_true", help="Skip direct HTTPS probes")
    ph.add_argument("--no-proxy-probe", action="store_true", help="Skip proxy forwarding probes")
    ph.set_defaults(func=cmd_proxy_health)

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
    er.add_argument("--latest", action="store_true", help="Latest proxy path diagnosis report (markdown)")
    er.add_argument("--analytics", action="store_true", help="Endpoint evidence analytics report (markdown)")
    er.add_argument("--url", default="", help="Target URL for network proof (legacy merged report)")
    er.add_argument("--fixture", default="", help="Optional fixture JSON for replay")
    er.add_argument("--format", choices=["json", "jsonl", "markdown", "html"], default="markdown")
    er.add_argument("--out", default="", help="Optional output file path")
    er.add_argument("--no-direct-probe", action="store_true", help="With --latest: skip direct HTTPS probes")
    er.add_argument("--no-proxy-probe", action="store_true", help="With --latest: skip proxy forwarding probes")
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

    ra = sub.add_parser("risk-assess", help="Technology risk assessment from case fixture (JSON)")
    ra.add_argument("--fixture", required=True, help="Case study fixture JSON path or name")
    ra.set_defaults(func=cmd_risk_assess)

    ct = sub.add_parser("control-test", help="Run control tests against case fixture (JSON)")
    ct.add_argument("--fixture", required=True, help="Case study fixture JSON path or name")
    ct.set_defaults(func=cmd_control_test)

    gr = sub.add_parser("governance-report", help="Governance / management report (fixture or audit-dir)")
    gr.add_argument("--fixture", default="", help="Case study fixture JSON path or name")
    gr.add_argument("--audit-dir", default="", help="Audit JSONL directory for audit-backed report")
    gr.add_argument("--risk-register", default="", help="Optional risk register JSON path")
    gr.add_argument("--format", choices=["json", "markdown", "html"], default="json")
    gr.set_defaults(func=cmd_governance_report)

    rks = sub.add_parser("risk-kpi-summary", help="Risk KPI rollup from audit JSONL (read-only)")
    rks.add_argument("--audit-dir", default="tests/fixtures/risk_analytics/audit_sample", help="Audit directory")
    rks.add_argument("--format", choices=["json", "markdown"], default="json")
    rks.set_defaults(func=cmd_risk_kpi_summary)

    ans = sub.add_parser("analytics-summary", help="Endpoint evidence analytics summary (read-only)")
    ans.add_argument("--input", default="", help="Audit JSONL file or directory (default: .audit)")
    ans.add_argument("--fixture", default="", help="Optional fixture JSON for deterministic replay")
    ans.add_argument("--audit-dir", default=".audit", help="Legacy platform audit dir (with --legacy-platform)")
    ans.add_argument("--legacy-platform", action="store_true", help="Use legacy platform_core risk analytics summarizer")
    ans.add_argument("--format", choices=["json", "markdown", "human"], default="human")
    ans.add_argument("--json", action="store_true", help="Emit JSON (same as --format json)")
    ans.add_argument("--bucket", choices=["day", "hour"], default="day", help="Timeline bucket granularity")
    ans.add_argument("--limit-processes", default="10", help="Top listener process limit")
    ans.set_defaults(func=cmd_analytics_summary)

    aex = sub.add_parser("analytics-export", help="Export endpoint analytics JSON/CSV (read-only)")
    aex.add_argument("--input", default="", help="Audit JSONL file or directory")
    aex.add_argument("--fixture", default="", help="Optional fixture JSON")
    aex.add_argument("--out", default="reports/analytics", help="Output directory")
    aex.add_argument("--format", choices=["json", "csv", "both"], default="both", help="Export format")
    aex.add_argument("--bucket", choices=["day", "hour"], default="day")
    aex.add_argument("--limit-processes", default="10")
    aex.set_defaults(func=cmd_analytics_export)

    pbi = sub.add_parser(
        "analytics-export-powerbi",
        help="Export Power BI-ready CSV tables from audit JSONL (read-only)",
    )
    pbi.add_argument(
        "--audit-dir",
        default="tests/fixtures/risk_analytics/audit_sample",
        help="Audit JSONL directory",
    )
    pbi.add_argument(
        "--out-dir",
        default="analytics/powerbi/data",
        help="Output directory for CSV files",
    )
    pbi.add_argument(
        "--portfolio-sample",
        action="store_true",
        help="Write deterministic portfolio sample CSVs (ignores audit-dir)",
    )
    pbi.add_argument(
        "--include-seed",
        action="store_true",
        help="Merge portfolio seed rows when audit dir is sparse",
    )
    pbi.set_defaults(func=cmd_analytics_export_powerbi)

    star = sub.add_parser(
        "powerbi-export",
        help="Export Power BI star schema semantic model pack (read-only)",
    )
    star.add_argument(
        "--audit-dir",
        default="tests/fixtures/risk_analytics/audit_sample",
        help="Audit JSONL directory",
    )
    star.add_argument(
        "--out-dir",
        default="examples/powerbi/export",
        help="Output directory for star schema CSV files",
    )
    star.add_argument(
        "--no-seed",
        action="store_true",
        help="Do not merge portfolio seed rows (audit-only export)",
    )
    star.set_defaults(func=cmd_powerbi_export)

    demo = sub.add_parser("demo", help="Golden fixture demo (read-only)")
    demo.set_defaults(func=cmd_demo)

    rd = sub.add_parser("reviewer-demo", help="Deterministic reviewer walkthrough (read-only)")
    rd.add_argument("--mode", choices=["big4", "faang", "mixed"], default="mixed")
    rd.add_argument("--out", default="", help="Optional demo-output directory for audit artifacts")
    rd.add_argument("--json", action="store_true", help="Emit summary JSON after walkthrough")
    rd.set_defaults(func=cmd_reviewer_demo)

    fs = sub.add_parser("fleet-simulate", help="Synthetic fleet audit JSONL (read-only)")
    fs.add_argument("--scenario", default="mixed_proxy_failures")
    fs.add_argument("--endpoints", default="100")
    fs.add_argument("--seed", default="42")
    fs.add_argument("--out", default="examples/fleet/audit_sample")
    fs.set_defaults(func=cmd_fleet_simulate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
