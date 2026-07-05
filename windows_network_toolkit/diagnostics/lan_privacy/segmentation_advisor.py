"""Network segmentation advisor — recommendation-only, preview mode.

Module responsibility:
    Emit prioritized, preview-only segmentation suggestions from inventory flags,
    classification, and optional router UPnP evidence.

System placement:
    Called by ``lan_privacy.runner`` and included in executive report output.

Key invariants:
    * Every ``SegmentationAdvice`` has ``preview_only=True`` — no config mutation.
    * Recommendations use conditional language; not enforcement or policy apply.
    * Absence of router evidence limits VLAN-specific advice to generic guidance.

Side effects:
    * None — pure recommendation generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import LanClassification


@dataclass
class SegmentationAdvice:
    priority: str
    title: str
    rationale: str
    limitations: list[str]
    preview_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def advise_segmentation(
    *,
    devices: list[dict[str, Any]],
    classification: str,
    has_router_evidence: bool,
    router_upnp_observed: bool = False,
) -> list[dict[str, Any]]:
    """Generate preview-only segmentation recommendations."""
    advice: list[SegmentationAdvice] = []
    unknown_iot = [d for d in devices if "unknown_vendor" in (d.get("flags") or [])]
    work_like = [
        d
        for d in devices
        if any(v in (d.get("vendor") or "").lower() for v in ("dell", "intel", "apple", "vmware"))
    ]
    casting = [d for d in devices if "iot_like" in (d.get("flags") or [])]

    if unknown_iot and work_like:
        advice.append(
            SegmentationAdvice(
                priority="HIGH",
                title="Guest Wi-Fi or VLAN for IoT",
                rationale=(
                    "Unknown-vendor devices observed on the same inventory as work-like devices. "
                    "Segmentation reduces blast radius — requires router admin action."
                ),
                limitations=["Recommendation only — tool does not change router settings."],
            )
        )

    if casting and work_like and not has_router_evidence:
        advice.append(
            SegmentationAdvice(
                priority="MEDIUM",
                title="Separate work laptops from smart TVs and casting devices",
                rationale=(
                    "Casting/IoT-like devices share the LAN with work devices. "
                    "Guest network isolation is a common SOHO control."
                ),
                limitations=["Cannot verify current VLAN segmentation without router evidence."],
            )
        )

    if router_upnp_observed:
        advice.append(
            SegmentationAdvice(
                priority="MEDIUM",
                title="Review UPnP exposure",
                rationale=(
                    "UPnP/SSDP activity observed. Consider disabling UPnP on router if unnecessary — "
                    "requires router-level review."
                ),
                limitations=["Host observation does not confirm WAN-side UPnP exposure."],
            )
        )

    if not has_router_evidence:
        advice.append(
            SegmentationAdvice(
                priority="MEDIUM",
                title="Enable router DNS filtering or logging",
                rationale=(
                    "No router logs imported (CTRL-LAN-007 gap). DNS logging improves outbound IoT visibility."
                ),
                limitations=["Cannot assess outbound DNS without router evidence import."],
            )
        )

    if classification in {
        LanClassification.BROAD_SUBNET_PROBING.value,
        LanClassification.POSSIBLE_LATERAL_RECON.value,
    }:
        advice.append(
            SegmentationAdvice(
                priority="HIGH",
                title="Investigate probing device isolation",
                rationale=(
                    "Possible reconnaissance pattern observed. Consider isolating the probing device "
                    "pending router or packet-capture evidence."
                ),
                limitations=["Suspicious is not confirmed compromise."],
            )
        )

    if not advice:
        advice.append(
            SegmentationAdvice(
                priority="LOW",
                title="Maintain baseline inventory",
                rationale="No immediate segmentation triggers — continue periodic lan-inventory reviews.",
                limitations=["Preview only."],
            )
        )

    return [a.to_dict() for a in advice]
