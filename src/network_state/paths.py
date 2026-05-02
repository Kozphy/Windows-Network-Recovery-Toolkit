"""Filesystem locations for Network State Manager artifacts."""

from __future__ import annotations

from pathlib import Path


def snapshots_jsonl(repo_root: Path) -> Path:
    return repo_root / "logs" / "network_state_snapshots.jsonl"


def default_profile_json(repo_root: Path) -> Path:
    return repo_root / "config" / "network_state_default.json"


def policy_json(repo_root: Path) -> Path:
    return repo_root / "config" / "network_state_policy.json"


def events_jsonl(repo_root: Path) -> Path:
    return repo_root / "logs" / "network_state_events.jsonl"


def audit_jsonl(repo_root: Path) -> Path:
    return repo_root / "logs" / "network_state_audit.jsonl"


def evidence_jsonl(repo_root: Path) -> Path:
    return repo_root / "logs" / "network_state_evidence.jsonl"


def report_txt(repo_root: Path) -> Path:
    return repo_root / "reports" / "network_state_report.txt"


def report_json(repo_root: Path) -> Path:
    return repo_root / "reports" / "network_state_report.json"
