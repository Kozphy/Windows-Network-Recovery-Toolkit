"""Threat catalog and asset mappings."""

from __future__ import annotations

from src.platform_core.enterprise.enums import RiskLevel
from src.platform_core.threats.models import Threat

THREATS: tuple[Threat, ...] = (
    Threat(
        threat_id="THR-001",
        name="Proxy Drift",
        description="WinINET proxy configuration drifts from approved baseline.",
        attack_vector="Misconfiguration / stale local proxy",
        likelihood=RiskLevel.MEDIUM,
        impact=RiskLevel.HIGH,
        asset_ids=["AST-PRX-001", "AST-REG-001", "AST-BRW-001"],
    ),
    Threat(
        threat_id="THR-002",
        name="Rogue Local Proxy",
        description="Unknown process listens on configured localhost proxy port.",
        attack_vector="Local listener correlation",
        likelihood=RiskLevel.MEDIUM,
        impact=RiskLevel.HIGH,
        asset_ids=["AST-PRX-001", "AST-EP-001"],
    ),
    Threat(
        threat_id="THR-003",
        name="Malware Persistence",
        description="Unauthorized re-application of proxy settings after remediation.",
        attack_vector="Registry writer / scheduled task (unproven without telemetry)",
        likelihood=RiskLevel.LOW,
        impact=RiskLevel.CRITICAL,
        asset_ids=["AST-REG-001", "AST-EP-001"],
    ),
    Threat(
        threat_id="THR-004",
        name="TLS Interception",
        description="Certificate path differs between direct and proxied connections.",
        attack_vector="Local MITM / debugging proxy",
        likelihood=RiskLevel.MEDIUM,
        impact=RiskLevel.CRITICAL,
        asset_ids=["AST-CERT-001", "AST-BRW-001", "AST-PRX-001"],
    ),
    Threat(
        threat_id="THR-005",
        name="Unauthorized Registry Modification",
        description="Proxy registry keys changed without approved change control.",
        attack_vector="HKCU Internet Settings modification",
        likelihood=RiskLevel.MEDIUM,
        impact=RiskLevel.HIGH,
        asset_ids=["AST-REG-001"],
    ),
    Threat(
        threat_id="THR-006",
        name="Configuration Drift",
        description="WinINET and WinHTTP paths diverge from expected baseline.",
        attack_vector="Split-stack proxy configuration",
        likelihood=RiskLevel.MEDIUM,
        impact=RiskLevel.MEDIUM,
        asset_ids=["AST-PRX-001", "AST-EP-001"],
    ),
)

_CLASSIFICATION_THREAT_MAP: dict[str, list[str]] = {
    "DEAD_PROXY_CONFIG": ["THR-001", "THR-006"],
    "UNKNOWN_LOCAL_PROXY": ["THR-002", "THR-005"],
    "TLS_PATH_MISMATCH": ["THR-004"],
    "REMEDIATION_NOT_STICKY": ["THR-003", "THR-001"],
    "WININET_WINHTTP_MISMATCH": ["THR-006"],
}


def threats_for_classification(classification: str) -> list[Threat]:
    ids = _CLASSIFICATION_THREAT_MAP.get(classification, ["THR-001"])
    id_set = set(ids)
    return [t for t in THREATS if t.threat_id in id_set]


def list_threats() -> list[Threat]:
    return list(THREATS)
