"""Unit tests for LinkedIn release-post draft generator."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "generate_linkedin_release_post.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_linkedin_release_post", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_linkedin_release_post"] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def test_strip_html_and_entities() -> None:
    assert "Hello World" in mod.strip_html("<p>Hello&nbsp;<b>World</b></p>")
    assert mod.strip_html("") == ""


def test_extract_improvements_from_bullets() -> None:
    notes = """
## Changes
- Evidence-based proxy drift diagnostics
* Policy-gated remediation previews
• Audit-ready JSONL exports
1. Monitoring dashboard (read-only)
"""
    items = mod.extract_improvements(notes, max_items=5)
    assert len(items) == 4
    assert "Evidence-based proxy drift diagnostics" in items[0]


def test_extract_improvements_empty_notes() -> None:
    assert mod.extract_improvements("") == []
    assert mod.extract_improvements("No bullets here, just prose.") == []


def test_extract_improvements_skips_secret_like_lines() -> None:
    notes = "- api_key=supersecret\n- Safe bullet about dry-run defaults"
    items = mod.extract_improvements(notes)
    assert len(items) == 1
    assert "dry-run" in items[0]


def test_build_post_uses_fallback_when_no_bullets() -> None:
    info = mod.ReleaseInfo(
        repository="Kozphy/Windows-Network-Recovery-Toolkit",
        release_name="v0.2.0",
        tag="v0.2.0",
        release_url="https://github.com/Kozphy/Windows-Network-Recovery-Toolkit/releases/tag/v0.2.0",
        notes="",
        published_at="2026-07-12T00:00:00Z",
    )
    draft = mod.build_post(info)
    assert "I've released v0.2.0" in draft
    assert "Windows Network Recovery Toolkit" in draft
    assert "See the GitHub release notes" in draft
    assert info.release_url in draft
    assert "#TechnologyRisk" in draft


def test_enforce_max_length() -> None:
    long = "x" * 100
    out = mod.enforce_max_length(long, 50)
    assert len(out) <= 50
    assert out.endswith("…")
    with pytest.raises(ValueError):
        mod.enforce_max_length("hi", 10)


def test_webhook_payload_shape() -> None:
    info = mod.ReleaseInfo(
        repository="org/repo",
        release_name="Rel",
        tag="v1",
        release_url="https://example.com/r",
        notes="- One",
        published_at="t",
    )
    draft = mod.build_post(info)
    payload = mod.build_webhook_payload(info, draft)
    assert payload["approval_required"] is True
    assert set(payload) >= {
        "repository",
        "release_name",
        "tag",
        "release_url",
        "draft",
        "approval_required",
    }
    dumped = json.dumps(payload)
    assert "ZAPIER_LINKEDIN_WEBHOOK_URL" not in dumped


def test_issue_marker_idempotency_helpers() -> None:
    assert mod.issue_marker("v1.2.3") == "<!-- linkedin-release-draft:v1.2.3 -->"
    assert mod.sanitize_tag_for_filename("release/v1.2.3") == "release-v1.2.3"
    body = mod.build_issue_body(
        mod.ReleaseInfo("a/b", "N", "v1", "https://x", "", "t"),
        "draft text",
    )
    assert mod.issue_marker("v1") in body
    assert "Technical claims verified" in body
    assert "Ready to publish" in body


def test_write_draft_files(tmp_path: Path) -> None:
    info = mod.release_info_from_mapping(
        {
            "repository": "Kozphy/Windows-Network-Recovery-Toolkit",
            "name": "Demo",
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/Kozphy/Windows-Network-Recovery-Toolkit/releases/tag/v9.9.9",
            "body": "- Procmon-assisted writer attribution path\n- Proxy-watch soak testing hooks",
            "published_at": "2026-07-12",
            "validation_summary": "Focused unit tests for the draft generator passed.",
        }
    )
    draft = mod.build_post(info)
    md_path, json_path = mod.write_draft_files(info, draft, root=tmp_path)
    assert md_path.name == "linkedin-v9.9.9.md"
    assert md_path.is_file()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["approval_required"] is True
    assert "Procmon-assisted" in draft
