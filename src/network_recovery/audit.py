"""Append-only audit sink for network recovery scenario runs."""

from __future__ import annotations

from pathlib import Path

from ..logging.audit import append_jsonl
from .models import AuditRecord, DiagnosisResult


def network_recovery_audit_path(repo_root: Path) -> Path:
    return repo_root / "logs" / "network_recovery_events.jsonl"


def append_network_recovery_audit(repo_root: Path, result: DiagnosisResult) -> Path:
    """Append one diagnosis row; returns the log path."""
    path = network_recovery_audit_path(repo_root)
    append_jsonl(path, AuditRecord.from_diagnosis(result).payload)
    return path
