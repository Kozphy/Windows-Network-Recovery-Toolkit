"""Read-only evidence collectors for localhost proxy drift investigations."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.models import registry_with_parsed
from ..proxy_guard.localhost_attribution import build_localhost_proxy_attribution
from ..proxy_guard.process_inventory import capture_process_inventory, heuristic_proxy_actor_candidates
from ..proxy_guard.registry import read_proxy_registry
from ..proxy_guard.snapshot_capture import capture_proxy_snapshot


def load_optional_before_snapshot(repo_root: Path) -> dict[str, Any] | None:
    """Load youngest LKG proxy snapshot if present (for drift context only)."""
    for candidate in (
        repo_root / "reports" / "proxy_guard_lkg.json",
        repo_root / "logs" / "proxy_known_good_snapshots.jsonl",
    ):
        if not candidate.is_file():
            continue
        try:
            if candidate.suffix == ".jsonl":
                last: dict[str, Any] | None = None
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(row, dict):
                        last = row.get("snapshot") if isinstance(row.get("snapshot"), dict) else row
                if last:
                    return last
            else:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError):
            continue
    return None


def collect_proxy_state(*, run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """HKCU WinINET, WinHTTP, env, git/npm proxy surfaces."""
    reg = read_proxy_registry(run=run)
    snap = capture_proxy_snapshot(registry_snapshot=reg, run=run)
    return {
        "registry_path": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        "proxy_enable": snap.proxy_enable,
        "proxy_server": snap.proxy_server,
        "proxy_override": snap.proxy_override,
        "auto_config_url": snap.auto_config_url,
        "auto_detect": snap.auto_detect,
        "winhttp": {
            "raw": snap.winhttp_proxy,
            "direct_access": snap.winhttp_direct_access,
            "proxy_server_literal": snap.winhttp_proxy_server_literal,
        },
        "environment": {
            "HTTP_PROXY": snap.user_http_proxy,
            "HTTPS_PROXY": snap.user_https_proxy,
            "ALL_PROXY": snap.user_all_proxy,
            "NO_PROXY": snap.user_no_proxy,
        },
        "git": {"http.proxy": snap.git_http_proxy, "https.proxy": snap.git_https_proxy},
        "npm": {"proxy": snap.npm_proxy, "https-proxy": snap.npm_https_proxy},
        "captured_at": snap.captured_at,
        "parsed_proxy": registry_with_parsed(reg).get("parsed_proxy"),
    }


def collect_listener_evidence(*, run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """netstat/CIM listener correlation for localhost proxy port."""
    reg = read_proxy_registry(run=run)
    merged = registry_with_parsed(reg)
    from ..proxy_guard.parser import parse_proxy_server

    p = parse_proxy_server(reg.proxy_server)
    block = build_localhost_proxy_attribution(reg, p, run=run)
    port = block.get("localhost_port")
    inventory = capture_process_inventory(proxy_localhost_port=port, run=run)
    return {
        "localhost_attribution": block,
        "process_inventory": inventory,
        "netstat_note": "Owners derived from netstat-ano and optional CIM enrichment.",
    }


def collect_dev_process_correlation(*, run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Correlate node/electron/IDE tooling — association only."""
    reg = read_proxy_registry(run=run)
    merged = registry_with_parsed(reg)
    parsed_raw = merged.get("parsed_proxy") or {}
    port = parsed_raw.get("localhost_port") if isinstance(parsed_raw, dict) else None
    inv = capture_process_inventory(proxy_localhost_port=port, run=run)
    rows = inv.get("process_rows") or []
    dev_rows: list[dict[str, Any]] = []
    from ..proxy_guard.attribution_model import ProxyActor

    actors: list[ProxyActor] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("process_name") or "").lower()
        if any(tok in name for tok in ("node", "electron", "code", "cursor", "npm", "python")):
            dev_rows.append(dict(r))
            try:
                pid = r.get("pid")
                if isinstance(pid, int):
                    actors.append(
                        ProxyActor(
                            pid=pid,
                            parent_pid=r.get("parent_pid") if isinstance(r.get("parent_pid"), int) else None,
                            process_name=r.get("process_name"),
                            image_path=r.get("executable_path"),
                            command_line=r.get("command_line"),
                            started_at=r.get("creation_time_utc"),
                        ),
                    )
            except (TypeError, ValueError):
                pass
    heuristic = [a.to_jsonable() for a in heuristic_proxy_actor_candidates(actors)]
    return {
        "dev_process_rows": dev_rows,
        "heuristic_candidates": heuristic,
        "listening_pids": inv.get("listening_pids") or [],
        "limitations": [
            "Process association detected — not proof of registry writer or malicious intent.",
        ],
    }
