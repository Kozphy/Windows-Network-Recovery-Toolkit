"""Export local DEAD_PROXY_CONFIG incident bundles (gitignored reports/)."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from windows_network_toolkit.diagnostics.proxy import run_proxy_status
from windows_network_toolkit.proxy_health import run_proxy_health_for_state
from windows_network_toolkit.proxy_state import collect_proxy_state_model


def _now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def export_dead_proxy_incident_bundle(
    *,
    repo_root: Path | None = None,
    audit_dir: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Copy watch audit log and fresh proxy snapshots into a local incident folder.

    Side effects:
        Writes under ``reports/dead_proxy_incident_<timestamp>/`` (gitignored).
        Does not mutate registry or commit machine data.
    """
    root = (repo_root or Path.cwd()).resolve()
    audit = (audit_dir or root / ".audit").resolve()
    stamp = _now_stamp()
    target = (out_dir or root / "reports" / f"dead_proxy_incident_{stamp}").resolve()
    target.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    watch_src = audit / "proxy-watch.jsonl"
    if watch_src.is_file():
        dest = target / "proxy-watch.jsonl"
        shutil.copy2(watch_src, dest)
        copied.append(str(dest.relative_to(root)))

    status = run_proxy_status()
    status_path = target / "proxy-status.json"
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    copied.append(str(status_path.relative_to(root)))

    state = collect_proxy_state_model().to_dict()
    health = run_proxy_health_for_state(state)
    health_path = target / "proxy-health.json"
    health_path.write_text(json.dumps(health, indent=2, sort_keys=True), encoding="utf-8")
    copied.append(str(health_path.relative_to(root)))

    readme = target / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "DEAD_PROXY_CONFIG incident bundle (local only — do not commit).",
                "Observation is not proof; classification is not accusation.",
                "",
                "Files:",
                *[f"  - {name}" for name in copied],
                "",
                "Next: review proxy-health.json classification, then proxy-disable --dry-run true",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "schema_version": "dead_proxy_incident_bundle.v1",
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_dir": str(target),
        "files": copied + [str(readme.relative_to(root))],
        "classification": status.get("classification"),
        "limitations": [
            "Local export only — not a formal audit opinion.",
            "Does not prove malware, MITM, or registry writer identity.",
        ],
    }
