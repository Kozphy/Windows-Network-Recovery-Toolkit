"""Continuous, prompt-free monitoring agent with a read-only default boundary.

The agent periodically executes an allowlisted set of observations, detects state
changes, records audit evidence, and emits escalation records. It never executes
remediation commands. Privileged actions remain external and approval-gated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG = logging.getLogger("wnrt.continuous_agent")
STOP_REQUESTED = False


@dataclass(frozen=True)
class Observation:
    check_id: str
    status: str
    summary: str
    details: dict[str, Any]
    observed_at: str
    fingerprint: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_allowlisted_command(command: list[str], timeout_seconds: int) -> dict[str, Any]:
    """Run only a command supplied by the trusted local configuration."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        shell=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def observe(check: dict[str, Any]) -> Observation:
    check_id = str(check["id"])
    check_type = str(check.get("type", "command"))
    observed_at = utc_now()

    try:
        if check_type == "command":
            command = check.get("command")
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError("command checks require a non-empty string list")
            result = run_allowlisted_command(command, int(check.get("timeout_seconds", 30)))
            expected = int(check.get("expected_exit_code", 0))
            status = "healthy" if result["returncode"] == expected else "degraded"
            summary = f"exit={result['returncode']} expected={expected}"
            details = result
        elif check_type == "file_exists":
            path = Path(str(check["path"]))
            exists = path.exists()
            expected = bool(check.get("expected", True))
            status = "healthy" if exists == expected else "degraded"
            summary = f"exists={exists} expected={expected}"
            details = {"path": str(path), "exists": exists}
        else:
            raise ValueError(f"unsupported check type: {check_type}")
    except Exception as exc:  # bounded failure becomes evidence, not process death
        status = "error"
        summary = f"{type(exc).__name__}: {exc}"
        details = {"error_type": type(exc).__name__, "error": str(exc)}

    fingerprint = stable_fingerprint({"status": status, "summary": summary, "details": details})
    return Observation(check_id, status, summary, details, observed_at, fingerprint)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("configuration root must be an object")
    return value


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"checks": {}}
    return load_json(path)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def request_stop(signum: int, _frame: Any) -> None:
    global STOP_REQUESTED
    LOG.info("stop requested by signal %s", signum)
    STOP_REQUESTED = True


def run_cycle(config: dict[str, Any], state: dict[str, Any], audit_path: Path, alerts_path: Path) -> None:
    checks = config.get("checks", [])
    if not isinstance(checks, list):
        raise ValueError("checks must be a list")

    previous_checks = state.setdefault("checks", {})
    for check in checks:
        if not isinstance(check, dict) or "id" not in check:
            raise ValueError("each check must be an object with an id")

        observation = observe(check)
        old = previous_checks.get(observation.check_id, {})
        changed = old.get("fingerprint") != observation.fingerprint
        record = {
            "event_type": "continuous_observation",
            "agent_mode": "read_only",
            "changed": changed,
            **asdict(observation),
        }
        append_jsonl(audit_path, record)

        alert_on = set(check.get("alert_on", ["degraded", "error"]))
        if observation.status in alert_on and (changed or bool(check.get("repeat_alerts", False))):
            append_jsonl(
                alerts_path,
                {
                    "event_type": "approval_or_review_required",
                    "action": "review",
                    "automatic_remediation": False,
                    **asdict(observation),
                },
            )

        previous_checks[observation.check_id] = {
            "fingerprint": observation.fingerprint,
            "status": observation.status,
            "observed_at": observation.observed_at,
        }

    state["last_cycle_at"] = utc_now()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the WNRT continuous read-only agent")
    parser.add_argument("--config", type=Path, default=Path("continuous_agent/config.example.json"))
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    config = load_json(args.config)
    interval = max(10, int(config.get("interval_seconds", 300)))
    state_path = Path(config.get("state_path", "artifacts/continuous-agent-state.json"))
    audit_path = Path(config.get("audit_path", "artifacts/continuous-agent-audit.jsonl"))
    alerts_path = Path(config.get("alerts_path", "artifacts/continuous-agent-alerts.jsonl"))
    state = load_state(state_path)

    LOG.info("continuous agent started: mode=read_only interval=%ss", interval)
    while not STOP_REQUESTED:
        started = time.monotonic()
        try:
            run_cycle(config, state, audit_path, alerts_path)
            save_state(state_path, state)
        except Exception:
            LOG.exception("monitoring cycle failed")
            append_jsonl(audit_path, {"event_type": "cycle_failure", "observed_at": utc_now()})

        if args.once:
            break
        remaining = max(0.0, interval - (time.monotonic() - started))
        deadline = time.monotonic() + remaining
        while not STOP_REQUESTED and time.monotonic() < deadline:
            time.sleep(min(1.0, deadline - time.monotonic()))

    LOG.info("continuous agent stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
