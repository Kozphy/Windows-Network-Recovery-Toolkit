"""Observe-only diagnose loop — prints suggestions only; never runs ``scripts/*.bat``."""

from __future__ import annotations

import argparse
import audit
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "2-minimal"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _run_once(repo: Path, *, fixture: Path | None) -> dict[str, object]:
    from core import actions as act
    from core import decision as dec
    from core import probes
    from core.features import to_dict as feats_to_dict

    if fixture is not None:
        features = probes.load_fixture(fixture)
        executed: list[dict[str, str]] = [{"label": "fixture", "cmd": str(fixture.resolve())}]
    else:
        features, meta = probes.collect(repo_root=repo)
        executed = list(meta.get("commands_executed") or [])

    result = dec.score(features)
    primary = result["primary"]
    issue = str(primary["issue"])
    plan = act.suggestions(issue, features)

    actions_rows = [{"title": a["title"], "script": a["script"], "risk": a["risk"]} for a in plan]

    diagnosis_id = str(uuid.uuid4())
    snapshot = {
        "diagnosis_id": diagnosis_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "features": feats_to_dict(features),
        "decision": {
            "issue": primary["issue"],
            "confidence": primary["confidence"],
            "reason": primary["reason"],
            "scores": result["scores"],
        },
        "suggested_actions": actions_rows,
        "commands_executed": executed,
    }

    audit.append(
        repo,
        {
            "type": "diagnosis",
            "diagnosis_id": diagnosis_id,
            "script_version": SCRIPT_VERSION,
            "issue": primary["issue"],
            "confidence": primary["confidence"],
            "reason": primary["reason"],
            "actions": actions_rows,
        },
    )
    audit.write_diagnosis(repo, snapshot)

    print(json.dumps(primary, indent=2, ensure_ascii=False))
    print("Suggested fixes (run manually — not launched from this agent):")
    for row in actions_rows:
        scr = row.get("script") or "(none)"
        print(f"  - {row['title']} [{row.get('risk')}] → {scr}")
    return snapshot


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Minimal network diagnosis loop (recommend-only).")
    p.add_argument("--fixture", type=Path, default=None, help="JSON feature fixture instead of live probes.")
    p.add_argument("--interval", type=float, default=0.0, help="Seconds between repeats (0 = exit after one pass).")
    p.add_argument("--repo-root", type=Path, default=None, help="Repo root default: alongside this script.")
    args = p.parse_args(argv)

    repo = (args.repo_root or _repo_root()).resolve()

    interval = float(args.interval)
    if interval < 0:
        interval = 0.0

    fixture: Path | None = args.fixture
    try:
        while True:
            _run_once(repo, fixture=fixture)
            if interval <= 0:
                break
            time.sleep(interval)
        return 0
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
