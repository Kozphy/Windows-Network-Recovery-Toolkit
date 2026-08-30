"""Detect and contain suspicious localhost WinINET rewriter persistence.

Module responsibility:
    Read-only detection of Session-0 / scheduled-task remote-load patterns that correlate
    with recurring localhost proxy rewrites, plus a **preview-default** containment path
    (disable/delete matching tasks, stop correlated processes, remove Defender exclusions,
    quarantine payload directories) gated by ``CONTAIN_LOCALHOST_REWRITER``.

System placement:
    Operator CLI ``python -m src contain-localhost-rewriter`` and
    ``contain-localhost-rewriter.cmd`` — not agent auto-plan, not silent kill.

Key invariants:
    * Dry-run / preview is the default; live apply requires the typed confirm token.
    * ``KILL_PROXY_PROCESS`` remains blocked in ``safety.py``; this is a distinct
      operator-gated composite action, not generic process kill.
    * Listener / task correlation is not registry-writer proof.
    * WNRT's own guardian / boot-trace tasks are never targeted.
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.logging.audit import append_jsonl

CONFIRM_CONTAIN = "CONTAIN_LOCALHOST_REWRITER"
_SCHEMA = "localhost_rewriter_containment.v1"

_REMOTE_IEX_RE = re.compile(
    r"(?is)iex\s*\(.*(?:iwr|invoke-webrequest)|"
    r"invoke-expression\s*\(.*(?:iwr|invoke-webrequest)|"
    r"downloadstring\s*\(",
)
_DEFENDER_EXCL_RE = re.compile(r"(?is)add-mppreference\s+.*exclusion")
_VERSION_UPDATER_RE = re.compile(r"(?i)versionupdater")
_SYSTEM32_PAYLOAD_RE = re.compile(
    r"(?i)\\windows\\system32\\(?!drivers\\)([^\\]+)\\(node\.exe|app\.js)",
)
_KNOWN_SYSTEM32_DIRS = frozenset(
    {
        "windows powershell",
        "windowspowershell",
        "wbem",
        "openssh",
        "driverstore",
        "config",
        "tasks",
        "spool",
        "com",
        "inetsrv",
    }
)

_LIMITATIONS = [
    "Detection is heuristic correlation — not malware attribution or registry-writer proof.",
    "Containment stops correlated persistence/listener processes; it does not prove they wrote ProxyEnable.",
    "Keep hold-direct guardian until logs/proxy_guardian.jsonl shows no further localhost rewrites.",
    "Generic KILL_PROXY_PROCESS remains blocked; this path requires CONTAIN_LOCALHOST_REWRITER.",
]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _is_wnrt_protected_task(task_name: str) -> bool:
    """True for WNRT-owned or OS built-in task paths that must never be deleted here."""
    name = (task_name or "").strip()
    if not name:
        return True
    upper = name.upper()
    if "WNRT-" in upper:
        return True
    if "\\MICROSOFT\\WINDOWS\\" in upper:
        return True
    return False


def _system32_payload_hit(text: str) -> bool:
    m = _SYSTEM32_PAYLOAD_RE.search(text or "")
    if not m:
        return False
    folder = (m.group(1) or "").strip().lower()
    return folder not in _KNOWN_SYSTEM32_DIRS


def score_task(task: dict[str, Any]) -> tuple[list[str], int]:
    """Return (signals, score) for a scheduled-task observation dict."""
    name = str(task.get("task_name") or task.get("name") or "")
    actions = str(task.get("actions") or task.get("command") or "")
    blob = f"{name}\n{actions}"
    signals: list[str] = []
    if _is_wnrt_protected_task(name):
        return [], 0
    if _REMOTE_IEX_RE.search(blob):
        signals.append("remote_iex_task")
    if _DEFENDER_EXCL_RE.search(blob):
        signals.append("defender_exclusion_task")
    if _VERSION_UPDATER_RE.search(blob):
        signals.append("version_updater_name")
    if _system32_payload_hit(blob):
        signals.append("system32_payload_ref")
    score = len(signals)
    if "remote_iex_task" in signals and "defender_exclusion_task" in signals:
        score += 1
    return signals, score


def score_process(proc: dict[str, Any]) -> tuple[list[str], int]:
    """Return (signals, score) for a process observation dict."""
    path = str(proc.get("executable_path") or proc.get("path") or "")
    cmd = str(proc.get("command_line") or proc.get("cmd") or "")
    parent_cmd = str(proc.get("parent_command_line") or "")
    blob = f"{path}\n{cmd}\n{parent_cmd}"
    signals: list[str] = []
    if _REMOTE_IEX_RE.search(blob):
        signals.append("remote_iex_process")
    if _VERSION_UPDATER_RE.search(blob):
        signals.append("version_updater_path")
    if _system32_payload_hit(blob):
        signals.append("system32_payload_process")
    score = len(signals)
    return signals, score


def match_threshold(task_signals: list[str], proc_signals: list[str], combined_score: int) -> bool:
    """True when evidence is strong enough to recommend containment."""
    if combined_score >= 3:
        return True
    if "version_updater_name" in task_signals or "version_updater_path" in proc_signals:
        return combined_score >= 2 or bool(task_signals and proc_signals)
    if "remote_iex_task" in task_signals and (
        "system32_payload_process" in proc_signals or "system32_payload_ref" in task_signals
    ):
        return True
    if "remote_iex_task" in task_signals and "defender_exclusion_task" in task_signals:
        return True
    return False


def _live_list_tasks(run: Callable[..., Any]) -> list[dict[str, Any]]:
    if platform.system() != "Windows":
        return []
    ps = (
        "$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue; "
        "foreach ($t in $tasks) { "
        "  $a = @($t.Actions | ForEach-Object { "
        "    (($_.Execute + ' ' + $_.Arguments).Trim()) "
        "  }) -join ' | '; "
        "  [PSCustomObject]@{ task_name = ($t.TaskPath + $t.TaskName); "
        "    state = [string]$t.State; actions = $a } "
        "} | ConvertTo-Json -Compress -Depth 4"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else [data]
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict) and item.get("task_name"):
            out.append(
                {
                    "task_name": str(item.get("task_name") or ""),
                    "state": str(item.get("state") or ""),
                    "actions": str(item.get("actions") or ""),
                }
            )
    return out


def _live_list_processes(run: Callable[..., Any]) -> list[dict[str, Any]]:
    if platform.system() != "Windows":
        return []
    ps = (
        "$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue; "
        "$byId = @{}; foreach ($p in $procs) { $byId[$p.ProcessId] = $p }; "
        "foreach ($p in $procs) { "
        "  $parent = $byId[$p.ParentProcessId]; "
        "  [PSCustomObject]@{ "
        "    pid = $p.ProcessId; name = $p.Name; session_id = $p.SessionId; "
        "    parent_pid = $p.ParentProcessId; "
        "    executable_path = $p.ExecutablePath; "
        "    command_line = $p.CommandLine; "
        "    parent_command_line = $(if ($parent) { $parent.CommandLine } else { $null }) "
        "  } "
        "} | ConvertTo-Json -Compress -Depth 4"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else [data]
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pid = item.get("pid")
        if pid is None:
            continue
        out.append(
            {
                "pid": int(pid),
                "name": str(item.get("name") or ""),
                "session_id": item.get("session_id"),
                "parent_pid": item.get("parent_pid"),
                "executable_path": str(item.get("executable_path") or "") or None,
                "command_line": str(item.get("command_line") or "") or None,
                "parent_command_line": str(item.get("parent_command_line") or "") or None,
            }
        )
    return out


def _live_list_exclusions(run: Callable[..., Any]) -> dict[str, list[str]]:
    if platform.system() != "Windows":
        return {"paths": [], "processes": []}
    ps = (
        "try { $p = Get-MpPreference -ErrorAction Stop; "
        "[PSCustomObject]@{ paths = @($p.ExclusionPath); "
        "processes = @($p.ExclusionProcess) } | ConvertTo-Json -Compress } "
        "catch { '{}' }"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"paths": [], "processes": []}
    raw = (proc.stdout or "").strip()
    if not raw:
        return {"paths": [], "processes": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"paths": [], "processes": []}
    if not isinstance(data, dict):
        return {"paths": [], "processes": []}
    paths = [str(x) for x in (data.get("paths") or []) if x]
    processes = [str(x) for x in (data.get("processes") or []) if x]
    return {"paths": paths, "processes": processes}


def detect_localhost_rewriter(
    *,
    tasks: list[dict[str, Any]] | None = None,
    processes: list[dict[str, Any]] | None = None,
    exclusions: dict[str, list[str]] | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Score scheduled tasks / processes for rewriter-persistence heuristics.

    Args:
        tasks: Optional injected task rows (tests); else live query.
        processes: Optional injected process rows (tests); else live query.
        exclusions: Optional Defender exclusion maps (tests); else live query.
        run: Optional ``subprocess.run`` surrogate.

    Returns:
        Detection envelope with ``match``, ``signals``, candidates, and limitations.
    """
    subprocess_run = run if run is not None else subprocess.run
    task_rows = tasks if tasks is not None else _live_list_tasks(subprocess_run)
    proc_rows = processes if processes is not None else _live_list_processes(subprocess_run)
    excl = exclusions if exclusions is not None else _live_list_exclusions(subprocess_run)

    matched_tasks: list[dict[str, Any]] = []
    matched_procs: list[dict[str, Any]] = []
    all_signals: list[str] = []
    best_score = 0

    for task in task_rows:
        signals, score = score_task(task)
        if score <= 0:
            continue
        row = {**task, "signals": signals, "score": score}
        matched_tasks.append(row)
        all_signals.extend(signals)
        best_score = max(best_score, score)

    for proc in proc_rows:
        signals, score = score_process(proc)
        if score <= 0:
            continue
        # Only keep processes that look related to suspicious payload / remote iex
        if score < 1:
            continue
        row = {**proc, "signals": signals, "score": score}
        matched_procs.append(row)
        all_signals.extend(signals)
        best_score = max(best_score, score)

    task_sig_set = sorted({s for t in matched_tasks for s in t.get("signals") or []})
    proc_sig_set = sorted({s for p in matched_procs for s in p.get("signals") or []})
    combined = len(set(task_sig_set) | set(proc_sig_set))
    # Boost when both sides present
    if matched_tasks and matched_procs:
        combined += 1
    matched = match_threshold(task_sig_set, proc_sig_set, combined)

    # Exclusion candidates tied to match
    excl_paths = [
        p
        for p in (excl.get("paths") or [])
        if _VERSION_UPDATER_RE.search(p) or _system32_payload_hit(p + "\\node.exe")
    ]
    excl_procs: list[str] = []
    if matched:
        for name in excl.get("processes") or []:
            if re.match(r"(?i)^powershell(\.exe)?$", name.strip()):
                excl_procs.append(name)
            if re.match(r"(?i)^node(\.exe)?$", name.strip()) and any(
                "system32_payload" in s for s in proc_sig_set
            ):
                excl_procs.append(name)

    payload_dirs: list[str] = []
    for proc in matched_procs:
        path = str(proc.get("executable_path") or "")
        m = _SYSTEM32_PAYLOAD_RE.search(path)
        if m:
            # directory containing node.exe / app.js
            payload_dirs.append(str(Path(path).parent))
        # Also from command lines that reference the folder
        cmd = str(proc.get("command_line") or "")
        m2 = re.search(r'(?i)([A-Z]:\\Windows\\System32\\VersionUpdater[^\\s"\']+)', cmd)
        if m2:
            payload_dirs.append(m2.group(1))
    for task in matched_tasks:
        actions = str(task.get("actions") or "")
        m3 = re.search(r'(?i)([A-Z]:\\Windows\\System32\\VersionUpdater[^\\s"\']+)', actions)
        if m3:
            payload_dirs.append(m3.group(1))
    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq_dirs: list[str] = []
    for d in payload_dirs:
        key = d.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq_dirs.append(d)

    return {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "match": matched,
        "signals": sorted(set(all_signals)),
        "score": combined,
        "matched_tasks": matched_tasks,
        "matched_processes": matched_procs,
        "exclusion_paths": excl_paths,
        "exclusion_processes": excl_procs,
        "payload_dirs": uniq_dirs,
        "limitations": list(_LIMITATIONS),
        "recommended_action": (
            f"Contain matched rewriter persistence (confirm {CONFIRM_CONTAIN}; dry-run false)."
            if matched
            else "No high-confidence rewriter persistence match."
        ),
    }


def _planned_steps(detection: dict[str, Any], quarantine_root: Path) -> list[str]:
    steps: list[str] = []
    for task in detection.get("matched_tasks") or []:
        name = task.get("task_name")
        if name:
            steps.append(f"Disable+delete scheduled task: {name}")
    for proc in detection.get("matched_processes") or []:
        pid = proc.get("pid")
        name = proc.get("name")
        if pid is not None:
            steps.append(f"Stop process PID {pid} ({name})")
    for path in detection.get("exclusion_paths") or []:
        steps.append(f"Remove Defender ExclusionPath: {path}")
    for proc in detection.get("exclusion_processes") or []:
        steps.append(f"Remove Defender ExclusionProcess: {proc}")
    for directory in detection.get("payload_dirs") or []:
        steps.append(f"Quarantine payload directory: {directory} -> {quarantine_root}")
    if not steps:
        steps.append("No containment steps (no match).")
    steps.append("Keep hold-direct guardian until rewrite stops in logs/proxy_guardian.jsonl")
    return steps


def _apply_live(
    detection: dict[str, Any],
    *,
    quarantine_root: Path,
    run: Callable[..., Any],
) -> dict[str, Any]:
    """Execute containment steps on Windows. Returns action detail dict."""
    details: dict[str, Any] = {
        "tasks_deleted": [],
        "processes_stopped": [],
        "exclusions_removed": [],
        "quarantined": [],
        "errors": [],
    }
    if platform.system() != "Windows":
        details["errors"].append("Containment apply requires Windows.")
        return details

    for task in detection.get("matched_tasks") or []:
        name = str(task.get("task_name") or "")
        if not name or _is_wnrt_protected_task(name):
            continue
        bare = name.split("\\")[-1] if "\\" in name else name
        try:
            run(
                ["schtasks", "/Change", "/TN", name, "/DISABLE"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            deleted = run(
                ["schtasks", "/Delete", "/TN", name, "/F"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if deleted.returncode != 0 and bare != name:
                deleted = run(
                    ["schtasks", "/Delete", "/TN", bare, "/F"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            if deleted.returncode == 0:
                details["tasks_deleted"].append(name)
            else:
                details["errors"].append(
                    f"Failed to delete task {name}: {(deleted.stderr or deleted.stdout or '').strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            details["errors"].append(f"Task delete error {name}: {exc}")

    for proc in detection.get("matched_processes") or []:
        pid = proc.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            continue
        try:
            stopped = run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if stopped.returncode == 0:
                details["processes_stopped"].append(pid)
            else:
                details["errors"].append(
                    f"Failed to stop PID {pid}: {(stopped.stderr or stopped.stdout or '').strip()}"
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            details["errors"].append(f"Stop PID {pid}: {exc}")

    for path in detection.get("exclusion_paths") or []:
        ps = f"Remove-MpPreference -ExclusionPath '{path.replace(chr(39), chr(39) * 2)}' -ErrorAction Stop"
        try:
            rem = run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if rem.returncode == 0:
                details["exclusions_removed"].append({"type": "path", "value": path})
            else:
                details["errors"].append(f"ExclusionPath remove failed: {path}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            details["errors"].append(f"ExclusionPath {path}: {exc}")

    for name in detection.get("exclusion_processes") or []:
        ps = f"Remove-MpPreference -ExclusionProcess '{name.replace(chr(39), chr(39) * 2)}' -ErrorAction Stop"
        try:
            rem = run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if rem.returncode == 0:
                details["exclusions_removed"].append({"type": "process", "value": name})
            else:
                details["errors"].append(f"ExclusionProcess remove failed: {name}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            details["errors"].append(f"ExclusionProcess {name}: {exc}")

    quarantine_root.mkdir(parents=True, exist_ok=True)
    for directory in detection.get("payload_dirs") or []:
        src = Path(directory)
        if not src.exists():
            details["errors"].append(f"Payload dir missing: {directory}")
            continue
        dest = quarantine_root / src.name
        try:
            # Best-effort ACL prep then move
            run(
                ["takeown", "/F", str(src), "/R", "/D", "Y"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            run(
                ["icacls", str(src), "/grant", "Administrators:F", "/T"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            shutil.move(str(src), str(dest))
            details["quarantined"].append({"from": str(src), "to": str(dest)})
        except (OSError, shutil.Error) as exc:
            details["errors"].append(f"Quarantine failed {directory}: {exc}")

    return details


def run_rewriter_containment(
    *,
    dry_run: bool = True,
    confirm: str = "",
    repo_root: Path | None = None,
    tasks: list[dict[str, Any]] | None = None,
    processes: list[dict[str, Any]] | None = None,
    exclusions: dict[str, list[str]] | None = None,
    run: Callable[..., Any] | None = None,
    apply_fn: Callable[..., dict[str, Any]] | None = None,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """Detect rewriter persistence and optionally contain it.

    Args:
        dry_run: When True (default), preview only.
        confirm: Must equal ``CONTAIN_LOCALHOST_REWRITER`` for live apply.
        repo_root: Toolkit root for quarantine/audit paths.
        tasks / processes / exclusions: Injectable observations for tests.
        run: Optional ``subprocess.run`` surrogate.
        apply_fn: Optional apply surrogate returning detail dict (tests).
        audit_path: Optional JSONL audit path.

    Returns:
        Governance-friendly result dict (match, planned_steps, action_taken, limitations).
    """
    subprocess_run = run if run is not None else subprocess.run
    root = (repo_root or Path.cwd()).resolve()
    quarantine_root = root / "reports" / "quarantine" / f"rewriter_{_stamp()}"
    log_path = audit_path or (root / "logs" / "rewriter_containment.jsonl")

    detection = detect_localhost_rewriter(
        tasks=tasks,
        processes=processes,
        exclusions=exclusions,
        run=subprocess_run,
    )
    planned = _planned_steps(detection, quarantine_root)
    result: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "dry_run": dry_run,
        "match": detection["match"],
        "signals": detection["signals"],
        "score": detection["score"],
        "matched_tasks": detection["matched_tasks"],
        "matched_processes": detection["matched_processes"],
        "exclusion_paths": detection["exclusion_paths"],
        "exclusion_processes": detection["exclusion_processes"],
        "payload_dirs": detection["payload_dirs"],
        "planned_steps": planned,
        "quarantine_root": str(quarantine_root),
        "action_taken": "none",
        "confirmation_required": CONFIRM_CONTAIN,
        "recommended_action": detection["recommended_action"],
        "limitations": list(_LIMITATIONS),
        "reason": "",
    }

    if not detection["match"]:
        result["reason"] = "No high-confidence rewriter persistence match."
        result["action_taken"] = "none"
        append_jsonl(log_path, {"event": "rewriter_containment_idle", **result})
        return result

    if dry_run:
        result["action_taken"] = "preview_only"
        result["reason"] = (
            "Rewriter persistence match — dry-run preview; no task/process/exclusion/quarantine changes."
        )
        append_jsonl(log_path, {"event": "rewriter_containment_preview", **result})
        return result

    if confirm != CONFIRM_CONTAIN:
        result["action_taken"] = "blocked"
        result["reason"] = f"Confirmation required: {CONFIRM_CONTAIN}"
        append_jsonl(log_path, {"event": "rewriter_containment_blocked", **result})
        return result

    apply = apply_fn if apply_fn is not None else _apply_live
    details = apply(detection, quarantine_root=quarantine_root, run=subprocess_run)
    result["apply"] = details
    errors = list(details.get("errors") or [])
    if errors and not (
        details.get("tasks_deleted")
        or details.get("processes_stopped")
        or details.get("quarantined")
        or details.get("exclusions_removed")
    ):
        result["action_taken"] = "failed"
        result["reason"] = "Containment attempted but no steps succeeded."
    else:
        result["action_taken"] = "remediated" if not errors else "remediated_with_errors"
        result["reason"] = "Containment applied for matched rewriter persistence."
    append_jsonl(log_path, {"event": "rewriter_containment_apply", **result})
    return result
