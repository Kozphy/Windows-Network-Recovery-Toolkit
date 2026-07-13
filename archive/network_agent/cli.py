from __future__ import annotations

"""CLI orchestration for hybrid network diagnosis and report generation.

This module sits at the application boundary and coordinates collectors,
decision logic, safety preview generation, and report persistence.

Pipeline position:
    ingestion (collectors) -> decision (engine) -> persistence (reports) ->
    presentation (CLI output).

Key invariants:
- Diagnosis runs before any repair-related guidance.
- Generated reports include policy metadata for auditability.
- CLI does not auto-execute repairs.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from .collectors import dns, firewall, https, proxy, tcp
from .engine.decision_engine import diagnose
from .reports.report_writer import build_report, write_report
from .safety.repair_policy import get_preview


def collect_snapshot() -> dict[str, dict[str, object]]:
    """Collect all subsystem snapshots into a single normalized structure.

    Input assumptions:
        - Collector modules are importable and executable on current host.
        - Collector outputs follow their documented schemas.

    Output guarantees:
        - Returns top-level keys: `dns`, `proxy`, `tcp`, `https`, `firewall`.
        - Each value is a JSON-serializable dict for downstream processing.

    Side effects:
        Executes collector subprocess calls (network/system probes).

    Idempotency:
        Operationally idempotent for unchanged host/network state.

    Args:
        None.

    Returns:
        dict[str, dict[str, object]]: Aggregated diagnostic snapshot.

    Raises:
        Any exception raised by collector imports or runtime failures not
        internally captured by collectors.

    Example:
        >>> snap = collect_snapshot()
        >>> sorted(snap.keys())
        ['dns', 'firewall', 'https', 'proxy', 'tcp']
    """
    return {
        "dns": dns.collect(),
        "proxy": proxy.collect(),
        "tcp": tcp.collect(),
        "https": https.collect(),
        "firewall": firewall.collect(),
    }


def run_diagnosis(reports_dir: Path) -> dict[str, Any]:
    """Execute the full diagnose-to-report pipeline once.

    Decision intent:
        Provide a single command entrypoint that produces both immediate
        diagnosis results and durable JSON artifacts for API/UI reuse.

    Output guarantees:
        - Returns a report dict with `report_id`, `diagnosis`, `policy`,
          `repair_preview`, and `report_path`.
        - Writes one report JSON file to `reports_dir`.

    Side effects:
        - Executes system/network probes via collectors.
        - Creates directories and writes report file to disk.

    Idempotency:
        Not strictly idempotent because each invocation creates a new report ID
        and timestamp, even if diagnosis content is unchanged.

    Args:
        reports_dir: Directory where report JSON files are persisted.

    Returns:
        dict[str, Any]: Enriched report payload including persisted file path.

    Raises:
        KeyError: If decision engine returns malformed diagnosis entries.
        OSError: If report directory/file creation fails.

    Example:
        >>> report = run_diagnosis(Path("reports"))
        >>> "report_path" in report
        True
    """
    snapshot = collect_snapshot()
    engine_output = diagnose(snapshot)
    top_action = engine_output["diagnosis"][0]["recommended_action"]
    repair_preview = get_preview(str(top_action))
    report = build_report(
        {
            "snapshot": snapshot,
            **engine_output,
            "repair_preview": repair_preview,
            "policy": {
                "diagnose_first": True,
                "destructive_repair_default": False,
                "firewall_reset_allowed": False,
                "confirmation_required": True,
            },
        }
    )
    path = write_report(report, reports_dir)
    report["report_path"] = str(path)
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for one-shot diagnosis runs.

    Args:
        None.

    Returns:
        argparse.ArgumentParser: Configured parser with output/report options.

    Raises:
        None.

    Example:
        >>> parser = build_parser()
        >>> parser.prog
        'network-agent'
    """
    parser = argparse.ArgumentParser(prog="network-agent")
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory where JSON reports are stored.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and print diagnosis output.

    Args:
        argv: Optional argument list override for testing/programmatic use.

    Returns:
        int: Process exit code (0 for success).

    Raises:
        Exceptions propagated from diagnosis and report pipeline operations.

    Example:
        >>> main(["--json"]) in (0, 1)
        True
    """
    args = build_parser().parse_args(argv)
    report = run_diagnosis(Path(args.reports_dir))
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("Hybrid AI Network Diagnostic Agent")
    print(f"Report ID: {report['report_id']}")
    print(f"Report Path: {report['report_path']}")
    print("Top diagnosis:")
    top = report["diagnosis"][0]
    print(f"- Issue: {top['issue']}")
    print(f"- Confidence: {top['confidence']}")
    print(f"- Recommended Action: {top['recommended_action']}")
    print("Use --json for full structured output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
