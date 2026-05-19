"""Append-only JSONL audit for proxy investigations."""

from __future__ import annotations

from pathlib import Path

from ..core.jsonl import append_jsonl as append_jsonl_core
from .constants import AUDIT_JSONL
from .models import ProxyInvestigationResult


def audit_path(repo_root: Path) -> Path:
    return repo_root / AUDIT_JSONL


def append_investigation(result: ProxyInvestigationResult, *, repo_root: Path) -> Path:
    path = audit_path(repo_root)
    payload = result.to_jsonable()
    payload["human_report_excerpt"] = result.human_report[:2000]
    append_jsonl_core(path, payload)
    return path
