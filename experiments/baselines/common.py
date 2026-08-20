"""Shared contracts for the fixture-only research baselines."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

TARGET_CLASSIFICATIONS = frozenset(
    {
        "BOTH_DIRECT_AND_PROXY_FAIL",
        "BOTH_DIRECT_AND_PROXY_WORK",
        "DEAD_PROXY_CONFIG",
        "DIRECT_ONLY_WORKS",
        "INSUFFICIENT_DATA",
        "LOCAL_PROXY_ACTIVE",
        "NO_PROXY_DIRECT_OK",
        "PROXY_ONLY_WORKS",
        "REVERTER_SUSPECTED",
        "UNKNOWN_LOCAL_PROXY",
        "WININET_WINHTTP_MISMATCH",
    }
)

ABSTENTION_CLASSIFICATIONS = frozenset(
    {"INSUFFICIENT_DATA", "INSUFFICIENT_EVIDENCE", "NOT_ENOUGH_EVIDENCE"}
)

SAFE_LIMITATIONS = (
    "Synthetic fixture result only; it does not establish production performance.",
    "Classification is triage guidance, not proof of malware, intent, or compromise.",
    "Benchmark adapters are read-only and never execute remediation.",
)


@dataclass(frozen=True)
class Prediction:
    """Normalized output shared by all benchmark adapters."""

    model_or_baseline: str
    predicted_class: str
    proof_tier: str
    limitations: tuple[str, ...]
    policy_decision: str
    supporting_signals: tuple[str, ...] = ()
    classification_supported: bool = True
    unsafe_action_proposed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json(value: Any) -> str:
    """Serialize a value for stable digests across supported platforms."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any) -> str:
    """Return a SHA-256 digest of canonical JSON."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_case(case: dict[str, Any], *, source: Path | None = None) -> None:
    """Validate the intentionally small research-case schema."""
    location = f" in {source}" if source else ""
    required = {"schema_version", "case_id", "split", "synthetic", "signals", "expected"}
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"research case{location} missing fields: {', '.join(missing)}")
    if case["schema_version"] != "research_case.v1":
        raise ValueError(f"research case{location} has unsupported schema_version")
    if case["split"] not in {"development", "held_out", "adversarial"}:
        raise ValueError(f"research case{location} has invalid split {case['split']!r}")
    if case["synthetic"] is not True:
        raise ValueError(f"research case{location} must explicitly declare synthetic=true")
    if not isinstance(case["signals"], dict):
        raise ValueError(f"research case{location} signals must be an object")
    expected = case["expected"]
    for field in ("classification", "minimum_proof_tier", "policy_decision"):
        if not isinstance(expected.get(field), str) or not expected[field].strip():
            raise ValueError(f"research case{location} expected.{field} must be non-empty")


def load_dataset(
    dataset_root: Path,
    *,
    splits: tuple[str, ...] | list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[Path]]:
    """Load cases in stable split/path order and reject duplicate identifiers."""
    selected = tuple(splits or ("development", "held_out", "adversarial"))
    cases: list[dict[str, Any]] = []
    paths: list[Path] = []
    seen: set[str] = set()
    for split in selected:
        split_dir = dataset_root / split
        if not split_dir.is_dir():
            raise FileNotFoundError(f"research split directory not found: {split_dir}")
        for path in sorted(split_dir.glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            validate_case(case, source=path)
            if case["split"] != split:
                raise ValueError(f"case {case['case_id']} declares split {case['split']}, expected {split}")
            case_id = str(case["case_id"])
            if case_id in seen:
                raise ValueError(f"duplicate research case_id: {case_id}")
            seen.add(case_id)
            cases.append(case)
            paths.append(path)
    if not cases:
        raise ValueError(f"no research cases found under {dataset_root}")
    return cases, paths


def dataset_inventory(dataset_root: Path, paths: list[Path]) -> tuple[str, list[dict[str, str]]]:
    """Digest canonical case content together with each relative path."""
    entries: list[dict[str, str]] = []
    combined = hashlib.sha256()
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        relative = path.relative_to(dataset_root).as_posix()
        case_sha = stable_digest(case)
        entries.append({"path": relative, "sha256": case_sha})
        combined.update(f"{relative}\n{case_sha}\n".encode())
    return combined.hexdigest(), entries


def verify_dataset_manifest(
    manifest_path: Path,
    *,
    dataset_root: Path,
    paths: list[Path],
) -> dict[str, Any]:
    """Fail closed when the frozen dataset differs from its checked-in manifest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest, entries = dataset_inventory(dataset_root, paths)
    if manifest.get("schema_version") != "research_dataset_manifest.v1":
        raise ValueError("unsupported research dataset manifest schema")
    if manifest.get("case_count") != len(paths):
        raise ValueError("research dataset manifest case_count mismatch")
    if manifest.get("sha256") != digest:
        raise ValueError("research dataset manifest sha256 mismatch")
    if manifest.get("files") != entries:
        raise ValueError("research dataset manifest file inventory mismatch")
    return manifest


def proof_tier_rank(value: str) -> int:
    """Return the ordinal T0-T7 prefix rank, or -1 for an invalid tier."""
    token = str(value).strip().upper()
    if len(token) >= 2 and token[0] == "T" and token[1].isdigit():
        rank = int(token[1])
        if 0 <= rank <= 7:
            return rank
    return -1


def proof_tier_meets_minimum(actual: str, minimum: str) -> bool:
    """Compare proof tiers by their explicit ordinal prefixes."""
    actual_rank = proof_tier_rank(actual)
    minimum_rank = proof_tier_rank(minimum)
    return actual_rank >= 0 and minimum_rank >= 0 and actual_rank >= minimum_rank


def is_localhost_proxy(server: Any) -> bool:
    """Conservatively identify the loopback forms used by synthetic fixtures."""
    value = str(server or "").strip().lower()
    return any(token in value for token in ("127.0.0.1", "localhost", "[::1]"))


def safe_policy_for_classification(classification: str) -> str:
    """Return a non-executing policy posture for simplified baselines."""
    if classification in {"DEAD_PROXY_CONFIG", "DIRECT_ONLY_WORKS"}:
        return "PREVIEW_ONLY"
    if classification in {
        "BOTH_DIRECT_AND_PROXY_FAIL",
        "INSUFFICIENT_DATA",
        "INSUFFICIENT_EVIDENCE",
        "NOT_ENOUGH_EVIDENCE",
        "REVERTER_SUSPECTED",
        "UNKNOWN_LOCAL_PROXY",
    }:
        return "REQUIRE_HUMAN_REVIEW"
    return "OBSERVE"
