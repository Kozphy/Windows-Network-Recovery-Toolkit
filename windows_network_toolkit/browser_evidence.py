"""Browser evidence package builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BrowserEvidencePackage(BaseModel):
    url: str
    screenshot_path: str = ""
    har_path: str = ""
    trace_path: str = ""
    navigation_error: str | None = None
    tls_errors: list[str] = Field(default_factory=list)
    proxy_hints: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Browser capture is path evidence — not malware or MITM confirmation.",
        ]
    )

    def to_raw_snapshot(self) -> dict[str, Any]:
        return {
            "browser_package": self.model_dump(),
            "proxy_state": {
                "browser_url": self.url,
                "navigation_error": self.navigation_error,
                "proxy_hints": self.proxy_hints,
            },
        }


def load_browser_package_from_fixture(fixture_path: Path) -> BrowserEvidencePackage:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return BrowserEvidencePackage.model_validate(data)


def summarize_har(har_path: Path) -> dict[str, Any]:
    if not har_path.is_file():
        return {"entries": 0, "failed": 0}
    try:
        har = json.loads(har_path.read_text(encoding="utf-8"))
        entries = har.get("log", {}).get("entries", [])
        failed = sum(1 for e in entries if e.get("response", {}).get("status", 0) >= 400)
        return {"entries": len(entries), "failed": failed}
    except (json.JSONDecodeError, OSError):
        return {"entries": 0, "failed": 0, "parse_error": True}
