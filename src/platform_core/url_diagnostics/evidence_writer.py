"""Persist URL diagnostic evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.platform_core.serialization import content_hash


def write_evidence(
    report: dict[str, Any],
    *,
    evidence_dir: str | Path,
    body_excerpt: str = "",
) -> list[str]:
    root = Path(evidence_dir)
    root.mkdir(parents=True, exist_ok=True)

    digest = content_hash({"url": report.get("input", {}).get("url"), "command": "url-diagnose"})[:12]
    files: list[str] = []

    report_path = root / f"url_diagnose_{digest}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    files.append(str(report_path))

    if body_excerpt:
        body_path = root / f"url_diagnose_{digest}_body.txt"
        body_path.write_text(body_excerpt[:16000], encoding="utf-8")
        files.append(str(body_path))

    return files
