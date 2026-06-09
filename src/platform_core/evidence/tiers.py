"""Canonical evidence tier vocabulary."""

from __future__ import annotations

from typing import Literal

EvidenceTier = Literal[
    "OBSERVED_ONLY",
    "CORRELATED",
    "PROVEN_REGISTRY_WRITER",
    "PROVEN_NETWORK_IMPACT",
    "FINAL_CAUSATION",
]

EVIDENCE_TIER_ORDER: tuple[EvidenceTier, ...] = (
    "OBSERVED_ONLY",
    "CORRELATED",
    "PROVEN_REGISTRY_WRITER",
    "PROVEN_NETWORK_IMPACT",
    "FINAL_CAUSATION",
)

_RANK = {t: i for i, t in enumerate(EVIDENCE_TIER_ORDER)}

# Legacy aliases (shim imports, older tests, proxy_guard vocabulary)
_LEGACY_MAP: dict[str, EvidenceTier] = {
    "OBSERVED_ONLY": "OBSERVED_ONLY",
    "CORRELATED": "CORRELATED",
    "CORRELATED_PROCESS": "CORRELATED",
    "PROVEN_REGISTRY_WRITER": "PROVEN_REGISTRY_WRITER",
    "PROVEN_NETWORK_IMPACT": "PROVEN_NETWORK_IMPACT",
    "PATH_VALIDATED": "PROVEN_NETWORK_IMPACT",
    "FINAL_CAUSATION": "FINAL_CAUSATION",
}


def tier_rank(tier: str | EvidenceTier) -> int:
    raw = str(tier).upper()
    normalized: EvidenceTier | str = _LEGACY_MAP.get(raw, raw)
    if normalized in _RANK:
        return _RANK[normalized]
    return -1


def normalize_tier(tier: str) -> EvidenceTier:
    key = str(tier).upper()
    if key in _LEGACY_MAP:
        return _LEGACY_MAP[key]
    for known in EVIDENCE_TIER_ORDER:
        if known == key:
            return known
    return "OBSERVED_ONLY"
