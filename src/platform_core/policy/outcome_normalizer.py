"""Normalize legacy/YAML policy outcomes to canonical gate vocabulary."""

from __future__ import annotations

from enum import StrEnum


class CanonicalPolicyGate(StrEnum):
    ALLOW = "ALLOW"
    PREVIEW = "PREVIEW"
    BLOCK = "BLOCK"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_ADMIN = "REQUIRE_ADMIN"
    REQUIRE_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"


_LEGACY_MAP: dict[str, CanonicalPolicyGate] = {
    "ALLOW": CanonicalPolicyGate.ALLOW,
    "ALLOW_OBSERVE": CanonicalPolicyGate.ALLOW,
    "ALLOW_PREVIEW": CanonicalPolicyGate.PREVIEW,
    "PREVIEW": CanonicalPolicyGate.PREVIEW,
    "PREVIEW_ONLY": CanonicalPolicyGate.PREVIEW,
    "OBSERVE": CanonicalPolicyGate.ALLOW,
    "BLOCK": CanonicalPolicyGate.BLOCK,
    "BLOCK_DESTRUCTIVE": CanonicalPolicyGate.BLOCK,
    "BLOCK_RECOMMENDED": CanonicalPolicyGate.BLOCK,
    "BLOCK_UNSAFE_ACTION": CanonicalPolicyGate.BLOCK,
    "BLOCK_AUTOMATION": CanonicalPolicyGate.BLOCK,
    "REQUIRE_TYPED_CONFIRMATION": CanonicalPolicyGate.REQUIRE_CONFIRMATION,
    "REQUIRE_CONFIRMATION": CanonicalPolicyGate.REQUIRE_CONFIRMATION,
    "REQUIRE_ADMIN": CanonicalPolicyGate.REQUIRE_ADMIN,
    "REQUIRE_HUMAN_APPROVAL": CanonicalPolicyGate.REQUIRE_HUMAN_REVIEW,
    "REQUIRE_HUMAN_REVIEW": CanonicalPolicyGate.REQUIRE_HUMAN_REVIEW,
    "HUMAN_REVIEW_REQUIRED": CanonicalPolicyGate.REQUIRE_HUMAN_REVIEW,
    "ESCALATE_REVIEW": CanonicalPolicyGate.REQUIRE_HUMAN_REVIEW,
    "CORRELATION_ONLY_ALERT": CanonicalPolicyGate.PREVIEW,
    "ROLLBACK_REQUIRED": CanonicalPolicyGate.REQUIRE_HUMAN_REVIEW,
}


def normalize_policy_outcome(outcome: str) -> CanonicalPolicyGate:
    key = str(outcome or "").strip().upper()
    if not key:
        return CanonicalPolicyGate.PREVIEW
    return _LEGACY_MAP.get(key, CanonicalPolicyGate.PREVIEW)
