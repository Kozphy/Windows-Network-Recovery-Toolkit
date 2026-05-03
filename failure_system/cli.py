"""Argument parsers for ``python -m failure_system`` workflows.

System placement:
    Mirrors FastAPI routes in ``failure_system.api`` while emitting JSON to stdout for scripting.

Side effects:
    ``diagnose`` mutates JSONL shards under ``FAILURE_SYSTEM_DATA_DIR`` or the default data directory.

Exit codes:
    ``0`` success, ``1`` missing recommendation match, ``2`` usage error—preserved for automation tests.

Audit Notes:
    Operators should redirect stdout when capturing evidence; stderr carries operator guidance only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

from failure_system.collector import collect_diagnostics
from failure_system.diagram_generator import (
    diagnosis_from_failure_run,
    generate_mermaid,
    snapshot_to_signal_dict,
)
from failure_system.explanation_text import generate_explanation_text
from failure_system.generator import build_failure_block
from failure_system.recommend import recommend_by_id, recommend_by_query
from failure_system.rules import RuleEngine
from failure_system.storage import append_failure_block, default_data_dir


def _data_dir_from_env() -> Path:
    """Resolve JSONL storage directory using the same rules as ``api.resolve_data_dir``.

    Returns:
        Absolute path from ``FAILURE_SYSTEM_DATA_DIR`` when set, else :func:`failure_system.storage.default_data_dir`.

    Raises:
        None.

    Side effects:
        Reads environment only.
    """

    env = os.environ.get("FAILURE_SYSTEM_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return default_data_dir()


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Run probes, emit JSON payload to stdout, append FailureBlock shard.

    Args:
        args: Parsed namespace including ``intermittent``, optional ``diagram``, ``diagram_file``.

    Returns:
        Exit code ``0`` after emitting JSON or Mermaid (see ``--diagram`` behavior).

    Raises:
        None — subprocess/tool failures are encoded inside ``DiagnosticSnapshot``.

    Safety constraints:
        Does not execute repair scripts; delegates probes to :func:`~failure_system.collector.collect_diagnostics`
        and appends JSONL read-only from other operators’ perspective except append side effect.

    Side effects:
        Appends one FailureBlock line via :func:`~failure_system.storage.append_failure_block`; may write Mermaid file if requested.
    """

    snapshot = collect_diagnostics(intermittent_reported=args.intermittent)
    outcomes = RuleEngine().evaluate(snapshot)
    block = build_failure_block(snapshot, outcomes)
    data_dir = _data_dir_from_env()
    path = append_failure_block(block, data_dir=data_dir)

    top = outcomes[0] if outcomes else None
    cause_str = top.cause if top else block.name
    risk = getattr(block.risk_level, "value", str(block.risk_level))
    diag_input = diagnosis_from_failure_run(
        snapshot_signals=snapshot_to_signal_dict(snapshot),
        owner_process=None,
        classification=None,
        cause=cause_str,
        confidence=float(block.confidence_score),
        risk_level=str(risk),
        recommended_fix=block.recommended_fix,
    )
    explanation_text = generate_explanation_text(diag_input)

    payload = {
        "failure_block": block.model_dump(mode="json"),
        "rule_outcomes": [o.model_dump(mode="json") for o in outcomes],
        "stored_path": str(path),
        "explanation_text": explanation_text,
    }

    diagram_flag = getattr(args, "diagram", False)
    diagram_path = getattr(args, "diagram_file", None)
    want_diagram = bool(diagram_flag) or bool(diagram_path)
    mermaid: str | None = None
    if want_diagram:
        mermaid = generate_mermaid(diag_input)

    if diagram_path and mermaid is not None:
        Path(diagram_path).write_text(mermaid, encoding="utf-8", newline="\n")

    if diagram_flag:
        print(mermaid or "")
        return 0

    print(json.dumps(payload, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Print JSON array of FailureBlocks matching the token-AND query.

    Args:
        args: Namespace with ``query`` string and ``limit`` integer.

    Returns:
        Exit code ``0``.

    Raises:
        None.

    Side effects:
        Read-only scan of JSONL shards under data dir; stdout JSON only.
    """

    from failure_system.search import search_failure_blocks

    hits = search_failure_blocks(args.query, data_dir=_data_dir_from_env(), limit=args.limit)
    print(json.dumps([h.model_dump(mode="json") for h in hits], indent=2))
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    """Emit ``FixRecommendation`` JSON for ``--id`` or first ``--query`` hit.

    Args:
        args: Namespace with optional ``id`` (UUID) or ``query`` text.

    Returns:
        ``0`` on hit; ``1`` no match; ``2`` invalid invocation printed to stderr.

    Raises:
        None.

    Side effects:
        Read-only JSONL access; stdout recommendation JSON only (no repair execution).
    """

    data_dir = _data_dir_from_env()
    rec = None
    if args.id:
        try:
            uid = UUID(args.id)
        except ValueError:
            print("Invalid UUID for --id", file=sys.stderr)
            return 2
        rec = recommend_by_id(uid, data_dir=data_dir)
    elif args.query:
        rec = recommend_by_query(args.query, data_dir=data_dir)
    else:
        print("Provide --id <uuid> or --query \"text\"", file=sys.stderr)
        return 2
    if rec is None:
        print("No recommendation found.", file=sys.stderr)
        return 1
    print(json.dumps(rec.model_dump(mode="json"), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``failure_system`` argparse tree without parsing argv.

    Returns:
        Root parser with ``diagnose``, ``search``, ``recommend`` subcommands.

    Raises:
        None.
    """

    p = argparse.ArgumentParser(
        prog="failure_system",
        description="Failure Knowledge System — safe diagnostics and FailureBlocks (no auto-repair).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("diagnose", help="Run safe probes, emit FailureBlock JSON, append JSONL shard.")
    d.add_argument(
        "--intermittent",
        action="store_true",
        help="Flag intermittent symptoms for rule engine weighting.",
    )
    d.add_argument(
        "--diagram",
        action="store_true",
        help="Print an explainable Mermaid flowchart (flowchart TD) instead of JSON.",
    )
    d.add_argument(
        "--diagram-file",
        type=Path,
        metavar="PATH",
        default=None,
        help="Write the same Mermaid diagram to PATH (.mmd). Implies diagram generation; stdout remains JSON unless --diagram is set.",
    )
    d.set_defaults(func=cmd_diagnose)

    s = sub.add_parser("search", help="Search persisted FailureBlocks by symptom/cause/output/fix text.")
    s.add_argument("query", help='Free-text query (token AND match).')
    s.add_argument("--limit", type=int, default=25, help="Max results (default 25).")
    s.set_defaults(func=cmd_search)

    r = sub.add_parser("recommend", help="Print FixRecommendation JSON for id or search query.")
    r.add_argument("--id", help="FailureBlock UUID from a prior diagnose run.")
    r.add_argument("--query", help="Search text when id is omitted.")
    r.set_defaults(func=cmd_recommend)

    return p


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to subcommand handlers.

    Args:
        argv: Optional argv list; defaults to process argv when ``None``.

    Returns:
        Integer exit code propagated from subcommands.

    Raises:
        ``SystemExit`` not raised here — callers receive integer codes.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
