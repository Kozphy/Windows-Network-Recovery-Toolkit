"""CLI for ``python -m toolkit``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from windows_network_toolkit.audit.replay import replay_to_dict
from windows_network_toolkit.audit.report_generator import generate_report


def cmd_replay(args: argparse.Namespace) -> int:
    path = Path(args.fixture)
    if not path.is_file():
        repo = Path(__file__).resolve().parents[1]
        path = repo / "windows_network_toolkit" / "examples" / args.fixture
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
    path = Path(args.fixture)
    if not path.is_file():
        repo = Path(__file__).resolve().parents[1]
        path = repo / "windows_network_toolkit" / "examples" / args.fixture
    payload = replay_to_dict(path, dry_run=True)
    text = generate_report(
        timeline=payload["timeline"],
        decision=payload["decision"],
        policy=payload["policy"],
        remediation=payload["remediation"],
        audit_rows=[payload.get("audit") or {}],
        fmt=args.format,  # type: ignore[arg-type]
    )
    print(text)
    return 0


def cmd_replay_certify(args: argparse.Namespace) -> int:
    from pathlib import Path

    from src.platform_core.replay.certifier import certify_case

    path = Path(args.fixture)
    if not path.is_file():
        repo = Path(__file__).resolve().parents[1]
        path = repo / "windows_network_toolkit" / "examples" / args.fixture
    cert = certify_case(jsonl_path=path)
    print(json.dumps({
        "certified": cert.certified,
        "certification_hash": cert.certification_hash,
        "tier": cert.tier,
        "policy_outcome": cert.policy_outcome,
        "errors": cert.errors,
    }, indent=2))
    return 0 if cert.certified else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toolkit", description="Endpoint Reliability Decision Platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay", help="Replay a JSONL incident fixture")
    replay.add_argument("fixture", help="Path to JSONL fixture")
    replay.add_argument("--format", choices=["json", "markdown"], default="markdown")
    replay.add_argument("--out", default="", help="Optional JSON output path")
    replay.set_defaults(func=cmd_replay)

    report = sub.add_parser("report", help="Generate audit report from fixture")
    report.add_argument("fixture", help="Path to JSONL fixture")
    report.add_argument("--format", choices=["json", "markdown", "html"], default="markdown")
    report.set_defaults(func=cmd_report)

    certify = sub.add_parser("replay-certify", help="Certify deterministic replay")
    certify.add_argument("fixture", help="Path to JSONL fixture")
    certify.set_defaults(func=cmd_replay_certify)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
