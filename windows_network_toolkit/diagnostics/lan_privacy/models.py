"""LAN privacy data models — devices, observations, classifications, limitations.

Module responsibility:
    Define schema version, evidence tiers, classification enums, and dataclass
    payloads shared across collectors, classifier, scoring, and reports.

System placement:
    Imported throughout ``windows_network_toolkit.diagnostics.lan_privacy`` and tests.

Key invariants:
    * ``LAN_LIMITATIONS`` must accompany user-facing outputs — not security verdicts.
    * ``EvidenceSource`` distinguishes host, router, and packet-capture tiers.
    * ``SCHEMA_VERSION`` tags all serialized LAN privacy artifacts.

Side effects:
    * None — types and constants only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = "wnt.lan_privacy.v1"

LAN_LIMITATIONS = [
    "Host-level observation is not proof of malicious intent.",
    "Scanning activity is not confirmed compromise without router or packet-capture evidence.",
    "Cannot confirm data exfiltration from Windows host telemetry alone.",
    "Attribution requires additional evidence beyond discovery protocol broadcasts.",
]


class EvidenceSource(StrEnum):
    HOST_LEVEL_OBSERVATION = "HOST_LEVEL_OBSERVATION"
    ROUTER_LEVEL_EVIDENCE = "ROUTER_LEVEL_EVIDENCE"
    PACKET_CAPTURE_EVIDENCE = "PACKET_CAPTURE_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class LanClassification(StrEnum):
    NORMAL_DISCOVERY = "NORMAL_DISCOVERY"
    NEW_DEVICE_OBSERVED = "NEW_DEVICE_OBSERVED"
    FREQUENT_DISCOVERY = "FREQUENT_DISCOVERY"
    BROAD_SUBNET_PROBING = "BROAD_SUBNET_PROBING"
    POSSIBLE_LATERAL_RECON = "POSSIBLE_LATERAL_RECON"
    UNKNOWN_IOT_DEVICE = "UNKNOWN_IOT_DEVICE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class LanProtocol(StrEnum):
    MDNS = "MDNS"
    SSDP = "SSDP"
    UPNP = "UPNP"
    NETBIOS = "NETBIOS"
    ARP = "ARP"
    ICMP = "ICMP"
    TCP_SYN = "TCP_SYN"


@dataclass
class LanDevice:
    ip: str
    mac: str = ""
    hostname: str = ""
    vendor: str = ""
    vendor_known: bool = True
    first_seen_utc: str = ""
    last_seen_utc: str = ""
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LanObservation:
    event_id: str
    timestamp_utc: str
    protocol: str
    source_ip: str = ""
    source_mac: str = ""
    target_ip: str = ""
    target_port: int = 0
    direction: str = "broadcast"
    evidence_source: str = EvidenceSource.HOST_LEVEL_OBSERVATION.value
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClassificationResult:
    primary_classification: str
    secondary_signals: list[str] = field(default_factory=list)
    confidence: float = 0.5
    reasoning: str = ""
    limitations: list[str] = field(default_factory=list)
    highest_evidence_source: str = EvidenceSource.HOST_LEVEL_OBSERVATION.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
