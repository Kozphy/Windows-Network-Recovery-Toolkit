"""Bounded ChatGPT/Electron process and Chromium network-state observations.

Module responsibility:
    Count matching ``ChatGPT.exe`` processes and locate the narrow Chromium
    ``Network Persistent State`` artifact used by known ChatGPT desktop layouts.

System placement:
    Read by network-recovery collectors and the policy-gated remediation executor.

Key invariants:
    * A process count is an observation, not proof that any process is hung.
    * File discovery is bounded to known ChatGPT user-data roots; no profile-wide scan.
    * Quarantine renames only an exact ``Network Persistent State`` file and is reversible.

Side effects:
    Observation helpers are read-only. ``quarantine_network_state_files`` renames files
    supplied from bounded discovery and must only be called after policy confirmation.
"""

from __future__ import annotations

import csv
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

NETWORK_STATE_FILENAME = "Network Persistent State"
PROCESS_FANOUT_REVIEW_THRESHOLD = 50


def parse_tasklist_process_count(output: str, *, image_name: str = "ChatGPT.exe") -> int:
    """Count exact image-name rows in ``tasklist /FO CSV`` output."""
    count = 0
    for row in csv.reader(output.splitlines()):
        if row and row[0].strip().casefold() == image_name.casefold():
            count += 1
    return count


def collect_process_count(
    image_name: str = "ChatGPT.exe",
    *,
    run: Callable[..., Any] = subprocess.run,
    timeout: float = 15.0,
) -> tuple[int | None, str | None]:
    """Return an exact tasklist count, or ``None`` with a limitation on probe failure."""
    try:
        proc = run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Process count unavailable: {exc}"
    if int(proc.returncode) != 0:
        detail = ((proc.stderr or "") + (proc.stdout or "")).strip()
        return None, f"Process count unavailable: tasklist exit {proc.returncode}: {detail[:240]}"
    return parse_tasklist_process_count(proc.stdout or "", image_name=image_name), None


def _environment(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def chatgpt_user_data_roots(*, env: Mapping[str, str] | None = None) -> list[Path]:
    """Return known ChatGPT desktop user-data roots without recursive discovery."""
    values = _environment(env)
    roaming = values.get("APPDATA", "").strip()
    local = values.get("LOCALAPPDATA", "").strip()
    roots: list[Path] = []
    if roaming:
        roaming_path = Path(roaming)
        roots.extend(
            [
                roaming_path / "ChatGPT",
                roaming_path / "com.openai.chat",
                roaming_path / "OpenAI" / "ChatGPT",
            ]
        )
    if local:
        local_path = Path(local)
        roots.append(local_path / "ChatGPT")
        packages = local_path / "Packages"
        if packages.is_dir():
            for package in sorted(packages.glob("OpenAI.ChatGPT*")):
                if not package.is_dir():
                    continue
                roots.extend(
                    [
                        package / "LocalCache" / "Roaming" / "ChatGPT",
                        package / "LocalCache" / "Local" / "ChatGPT",
                        package / "RoamingState" / "ChatGPT",
                    ]
                )

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _bounded_state_candidates(root: Path) -> list[Path]:
    candidates = [
        root / "Network" / NETWORK_STATE_FILENAME,
        root / NETWORK_STATE_FILENAME,
        root / "Default" / "Network" / NETWORK_STATE_FILENAME,
        root / "User Data" / "Default" / "Network" / NETWORK_STATE_FILENAME,
    ]
    partitions = root / "Partitions"
    if partitions.is_dir():
        for partition in sorted(partitions.iterdir()):
            if partition.is_dir():
                candidates.append(partition / "Network" / NETWORK_STATE_FILENAME)
    return candidates


def discover_chatgpt_network_state_files(*, env: Mapping[str, str] | None = None) -> list[Path]:
    """Locate exact network-state files under known ChatGPT roots only."""
    files: list[Path] = []
    seen: set[str] = set()
    for root in chatgpt_user_data_roots(env=env):
        for candidate in _bounded_state_candidates(root):
            key = str(candidate).casefold()
            if key not in seen and candidate.is_file():
                seen.add(key)
                files.append(candidate)
    return files


def describe_network_state_location(path: Path, *, env: Mapping[str, str] | None = None) -> str:
    """Return an audit label with profile roots replaced by environment tokens."""
    values = _environment(env)
    raw = str(path)
    for variable in ("APPDATA", "LOCALAPPDATA"):
        base = values.get(variable, "").strip()
        if base and raw.casefold().startswith(str(Path(base)).casefold()):
            suffix = raw[len(str(Path(base))) :].lstrip("\\/").replace("/", "\\")
            return f"%{variable}%\\{suffix}"
    return path.name


def observe_chatgpt_network_state(*, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return metadata-only evidence; never read network-state file contents."""
    files = discover_chatgpt_network_state_files(env=env)
    return {
        "file_count": len(files),
        "locations": [describe_network_state_location(path, env=env) for path in files],
        "content_read": False,
        "limitation": (
            "Network Persistent State presence is normal Chromium behavior; presence alone "
            "does not prove corrupt QUIC or Happy Eyeballs state. Bounded discovery covers "
            "known ChatGPT layouts only; a zero count does not prove the artifact is absent."
        ),
    }


def _is_within_known_root(path: Path, roots: Sequence[Path]) -> bool:
    resolved = path.resolve(strict=False)
    return any(resolved.is_relative_to(root.resolve(strict=False)) for root in roots)


def quarantine_network_state_files(
    files: Sequence[Path],
    *,
    env: Mapping[str, str] | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Atomically rename exact state files to timestamped, reversible backups."""
    stamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    roots = chatgpt_user_data_roots(env=env)
    results: list[dict[str, Any]] = []
    for path in files:
        label = describe_network_state_location(path, env=env)
        row: dict[str, Any] = {"location": label, "status": "blocked", "backup": None}
        if path.name != NETWORK_STATE_FILENAME or not _is_within_known_root(path, roots):
            row["reason"] = "Path is outside the bounded ChatGPT network-state allowlist."
            results.append(row)
            continue
        if not path.is_file():
            row.update({"status": "absent", "reason": "State file no longer exists."})
            results.append(row)
            continue
        backup = path.with_name(f"{NETWORK_STATE_FILENAME}.wnrt-backup-{stamp}")
        suffix = 1
        while backup.exists():
            backup = path.with_name(f"{NETWORK_STATE_FILENAME}.wnrt-backup-{stamp}-{suffix}")
            suffix += 1
        try:
            path.replace(backup)
        except OSError as exc:
            row.update({"status": "failed", "reason": str(exc)})
        else:
            row.update(
                {
                    "status": "quarantined",
                    "reason": "Original path is free for Chromium to recreate.",
                    "backup": describe_network_state_location(backup, env=env),
                }
            )
        results.append(row)
    return results
