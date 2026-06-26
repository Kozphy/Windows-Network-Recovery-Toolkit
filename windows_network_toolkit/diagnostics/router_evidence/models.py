"""Router evidence models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

ROUTER_SCHEMA = "wnt.router_evidence.v1"


class RouterEventType(StrEnum):
    DNS = "dns"
    FIREWALL = "firewall"
    DHCP = "dhcp"
    DEVICE = "device"


@dataclass
class RouterEvent:
    event_id: str
    timestamp_utc: str
    event_type: str
    evidence_source: str = "ROUTER_LEVEL_EVIDENCE"
    client_ip: str = ""
    mac: str = ""
    domain: str = ""
    query: str = ""
    src_ip: str = ""
    dst_ip: str = ""
    port: int = 0
    action: str = ""
    hostname: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.event_type == RouterEventType.DNS.value:
            d["domain"] = self.domain or self.query
        return d
