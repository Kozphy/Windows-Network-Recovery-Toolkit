#!/usr/bin/env python3
"""Generate a LinkedIn release-post *draft* from GitHub Release metadata.

Module responsibility:
    Deterministically format a professional LinkedIn draft from release fields.
    Never publish to LinkedIn; never embed secrets in outputs.

System placement:
    Invoked by ``.github/workflows/linkedin-release-draft.yml`` and local tests.

Key invariants:
    * Stdlib only.
    * Empty release notes do not invent feature claims.
    * Webhook payload uses ``approval_required: true`` and contains no secrets.
    * Issue marker ``<!-- linkedin-release-draft:{tag} -->`` supports idempotent upserts.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MAX_LENGTH = 2800
DEFAULT_HASHTAGS = (
    "#TechnologyRisk",
    "#PlatformEngineering",
    "#SRE",
    "#Windows",
    "#OpenSource",
)
ISSUE_MARKER_TEMPLATE = "<!-- linkedin-release-draft:{tag} -->"
PROJECT_NAME = "Windows Network Recovery Toolkit"
PROJECT_ONE_LINER = (
    "Technology Risk & Control Analytics Platform for Windows endpoint evidence"
)

# Capability lines that are always true for this repository (not claimed as "new").
SAFE_CAPABILITY_BULLETS = (
    "Evidence-based proxy drift diagnostics with explicit proof tiers",
    "Policy-gated remediation previews (dry-run by default; typed confirmation)",
    "Append-only audit trails and governance-oriented limitations[] on outputs",
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+(.+)$")
_SECRET_HINT_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|webhook|bearer\s+[a-z0-9._-]+|"
    r"ghp_[a-z0-9]+|gho_[a-z0-9]+|sk-[a-z0-9]+)"
)


@dataclass(frozen=True)
class ReleaseInfo:
    """Normalized release fields for draft generation."""

    repository: str
    release_name: str
    tag: str
    release_url: str
    notes: str
    published_at: str
    validation_summary: str = ""


def issue_marker(tag: str) -> str:
    """Return the stable hidden HTML marker for issue idempotency."""

    cleaned = (tag or "").strip() or "unknown"
    return ISSUE_MARKER_TEMPLATE.format(tag=cleaned)


def sanitize_tag_for_filename(tag: str) -> str:
    """Map a git tag to a filesystem-safe fragment."""

    cleaned = (tag or "unknown").strip()
    cleaned = cleaned.replace("/", "-").replace("\\", "-")
    cleaned = re.sub(r"[^\w.\-+]+", "-", cleaned)
    return cleaned.strip("-._") or "unknown"


def strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities; preserve plain text."""

    if not text:
        return ""
    no_tags = _HTML_TAG_RE.sub(" ", text)
    unescaped = html.unescape(no_tags).replace("\xa0", " ")
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"[ \t]{2,}", " ", unescaped)).strip()


def extract_improvements(notes: str, *, max_items: int = 5) -> list[str]:
    """Extract up to *max_items* bullet-like improvements from release notes.

    Returns an empty list when notes are missing or contain no bullets — callers
    must not invent release-specific features.
    """

    plain = strip_html(notes or "")
    if not plain.strip():
        return []

    found: list[str] = []
    for line in plain.splitlines():
        match = _BULLET_RE.match(line)
        if not match:
            continue
        item = match.group(1).strip()
        item = re.sub(r"\s+", " ", item)
        if not item or _SECRET_HINT_RE.search(item):
            continue
        if item not in found:
            found.append(item)
        if len(found) >= max_items:
            break
    return found


def _default_whats_new() -> list[str]:
    """Conservative bullets when release notes have no list items."""

    return [
        "See the GitHub release notes for tag-specific changes.",
        *SAFE_CAPABILITY_BULLETS[:2],
    ]


def build_post(
    info: ReleaseInfo,
    *,
    max_length: int = DEFAULT_MAX_LENGTH,
    hashtags: tuple[str, ...] = DEFAULT_HASHTAGS,
) -> str:
    """Format a LinkedIn draft. Truncates to *max_length* if needed."""

    name = (info.release_name or info.tag or "this release").strip()
    improvements = extract_improvements(info.notes)
    if not improvements:
        improvements = _default_whats_new()

    bullets = "\n".join(f"• {item}" for item in improvements[:5])
    tags = " ".join(hashtags[:5])

    why = (
        f"{PROJECT_ONE_LINER}: collect endpoint proxy evidence, classify with proof tiers, "
        "preview policy-gated remediation, and retain audit-ready outputs - without claiming "
        "antivirus verdicts or autonomous repair."
    )

    validation = (info.validation_summary or "").strip()
    if not validation:
        validation = (
            "Validate locally with the repository test suite and safety contracts before "
            "publishing any public claims about counts or results."
        )
    elif _SECRET_HINT_RE.search(validation):
        validation = (
            "Validation summary omitted because it contained patterns that may be sensitive."
        )

    draft = (
        f"I've released {name} of my {PROJECT_NAME}.\n\n"
        f"What's new:\n{bullets}\n\n"
        f"Why it matters:\n{why}\n\n"
        f"Validation:\n{validation}\n\n"
        f"GitHub:\n{info.release_url.strip()}\n\n"
        f"{tags}"
    )
    return enforce_max_length(draft, max_length)


def enforce_max_length(text: str, max_length: int) -> str:
    """Truncate text to *max_length*, preferring a clean ellipsis boundary."""

    if max_length < 32:
        raise ValueError("max_length must be >= 32")
    if len(text) <= max_length:
        return text
    cut = text[: max_length - 1].rstrip()
    # Prefer cutting at last newline if near the end
    nl = cut.rfind("\n")
    if nl > max_length // 2:
        cut = cut[:nl].rstrip()
    return cut + "…"


def build_webhook_payload(info: ReleaseInfo, draft: str) -> dict[str, Any]:
    """JSON-serializable webhook body for Zapier (draft only; approval required)."""

    return {
        "repository": info.repository,
        "release_name": info.release_name,
        "tag": info.tag,
        "release_url": info.release_url,
        "draft": draft,
        "approval_required": True,
        "published_at": info.published_at,
    }


def build_issue_body(info: ReleaseInfo, draft: str) -> str:
    """Markdown body for the review issue, including marker and checklist."""

    marker = issue_marker(info.tag)
    return (
        f"{marker}\n"
        f"# LinkedIn draft: {info.release_name or info.tag}\n\n"
        f"**Release:** [{info.tag}]({info.release_url})\n\n"
        f"**Published:** {info.published_at or '(not set)'}\n\n"
        f"**Repository:** `{info.repository}`\n\n"
        f"## Draft (do not auto-publish)\n\n"
        f"```text\n{draft}\n```\n\n"
        f"## Approval checklist\n\n"
        f"- [ ] Technical claims verified\n"
        f"- [ ] Test count verified\n"
        f"- [ ] No confidential information included\n"
        f"- [ ] Ready to publish\n\n"
        f"## Notes\n\n"
        f"- This issue is maintained by the LinkedIn release-draft workflow.\n"
        f"- Re-runs update this issue instead of opening duplicates (marker: `{marker}`).\n"
        f"- Optional Zapier webhook receives the draft with `approval_required: true` only.\n"
    )


def artifact_path_for_tag(tag: str, *, root: Path) -> Path:
    """Return ``artifacts/linkedin/linkedin-{tag}.md`` under *root*."""

    return root / "artifacts" / "linkedin" / f"linkedin-{sanitize_tag_for_filename(tag)}.md"


def write_draft_files(
    info: ReleaseInfo,
    draft: str,
    *,
    root: Path,
) -> tuple[Path, Path]:
    """Write markdown draft and JSON sidecar (webhook payload shape, no secrets)."""

    out = artifact_path_for_tag(info.tag, root=root)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"<!-- generated by scripts/generate_linkedin_release_post.py -->\n"
        f"{issue_marker(info.tag)}\n\n"
        f"# LinkedIn draft — {info.release_name or info.tag}\n\n"
        f"- Repository: `{info.repository}`\n"
        f"- Tag: `{info.tag}`\n"
        f"- Release URL: {info.release_url}\n"
        f"- Published: {info.published_at or '(not set)'}\n\n"
        f"## Post body\n\n"
        f"```text\n{draft}\n```\n"
    )
    out.write_text(body, encoding="utf-8")
    payload_path = out.with_suffix(".json")
    payload_path.write_text(
        json.dumps(build_webhook_payload(info, draft), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out, payload_path


def release_info_from_mapping(raw: dict[str, Any]) -> ReleaseInfo:
    """Build ``ReleaseInfo`` from a JSON object (event or mock)."""

    return ReleaseInfo(
        repository=str(raw.get("repository") or raw.get("repo") or "").strip(),
        release_name=str(raw.get("release_name") or raw.get("name") or "").strip(),
        tag=str(raw.get("tag") or raw.get("tag_name") or "").strip(),
        release_url=str(raw.get("release_url") or raw.get("html_url") or "").strip(),
        notes=str(raw.get("notes") or raw.get("body") or ""),
        published_at=str(raw.get("published_at") or "").strip(),
        validation_summary=str(raw.get("validation_summary") or "").strip(),
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-json", type=Path, help="Path to release JSON payload")
    parser.add_argument("--repository", default="")
    parser.add_argument("--release-name", default="")
    parser.add_argument("--tag", default="")
    parser.add_argument("--release-url", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--published-at", default="")
    parser.add_argument("--validation-summary", default="")
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--write-artifact", action="store_true")
    parser.add_argument("--print-issue-body", action="store_true")
    parser.add_argument("--print-webhook-json", action="store_true")
    parser.add_argument("--print-marker", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    raw: dict[str, Any] = {}
    if args.release_json:
        raw = json.loads(args.release_json.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            print("release JSON must be an object", file=sys.stderr)
            return 2

    notes = args.notes
    if args.notes_file:
        notes = args.notes_file.read_text(encoding="utf-8")

    merged = {
        **raw,
        **{
            k: v
            for k, v in {
                "repository": args.repository,
                "release_name": args.release_name,
                "tag": args.tag,
                "release_url": args.release_url,
                "notes": notes,
                "published_at": args.published_at,
                "validation_summary": args.validation_summary,
            }.items()
            if v
        },
    }
    info = release_info_from_mapping(merged)
    if not info.tag:
        print("tag is required", file=sys.stderr)
        return 2
    if not info.release_url:
        info = ReleaseInfo(
            repository=info.repository or "unknown/repo",
            release_name=info.release_name or info.tag,
            tag=info.tag,
            release_url=f"https://github.com/{info.repository}/releases/tag/{info.tag}"
            if info.repository
            else "",
            notes=info.notes,
            published_at=info.published_at,
            validation_summary=info.validation_summary,
        )

    draft = build_post(info, max_length=int(args.max_length))

    if args.print_marker:
        print(issue_marker(info.tag))
        return 0
    if args.print_webhook_json:
        print(json.dumps(build_webhook_payload(info, draft), ensure_ascii=False))
        return 0
    if args.print_issue_body:
        print(build_issue_body(info, draft))
        return 0

    if args.write_artifact:
        md_path, json_path = write_draft_files(info, draft, root=args.repo_root)
        print(json.dumps({"draft_path": str(md_path), "payload_path": str(json_path), "draft": draft}))
        return 0

    print(draft)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
