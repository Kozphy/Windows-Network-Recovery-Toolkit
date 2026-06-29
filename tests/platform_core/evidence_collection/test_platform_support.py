"""Tests for endpoint evidence collection platform support levels."""

from __future__ import annotations

from src.platform_core.evidence_collection import (
    collect_endpoint_evidence,
    get_endpoint_evidence_collector,
)
from src.platform_core.evidence_collection.darwin import DarwinEndpointEvidenceCollector
from src.platform_core.evidence_collection.linux import LinuxEndpointEvidenceCollector
from src.platform_core.evidence_collection.unsupported import UnsupportedPlatformEvidenceCollector
from src.platform_core.evidence_collection.windows import WindowsEndpointEvidenceCollector


def test_factory_windows_full_support() -> None:
    collector = get_endpoint_evidence_collector("windows")
    assert isinstance(collector, WindowsEndpointEvidenceCollector)
    bundle = collector.collect_bundle()
    assert bundle.platform_support_level == "FULL"
    assert bundle.os_family == "windows"
    assert bundle.collector_id == "windows_network_diagnostics_v1"
    assert bundle.observations
    assert bundle.limitations
    assert bundle.live_remediation_supported is True


def test_factory_linux_partial_support() -> None:
    collector = get_endpoint_evidence_collector("linux")
    assert isinstance(collector, LinuxEndpointEvidenceCollector)
    bundle = collector.collect_bundle()
    assert bundle.platform_support_level == "PARTIAL"
    assert bundle.os_family == "linux"
    assert bundle.live_remediation_supported is False
    assert any("WinINET" in note or "wininet" in note.lower() for note in bundle.limitations)
    assert bundle.observations


def test_factory_darwin_partial_support_no_wininet_claims() -> None:
    collector = get_endpoint_evidence_collector("darwin")
    assert isinstance(collector, DarwinEndpointEvidenceCollector)
    bundle = collector.collect_bundle()
    assert bundle.platform_support_level == "PARTIAL"
    assert bundle.os_family == "darwin"
    assert bundle.collector_id == "darwin_network_diagnostics_v1"
    assert bundle.live_remediation_supported is False
    assert any("networksetup" in note.lower() for note in bundle.limitations)
    signal_names = {row["signal_name"] for row in bundle.observations}
    assert "os_family" in signal_names
    assert "proxy_enable" not in signal_names
    assert "winhttp_proxy_state" not in signal_names
    assert "listening_port_probe_available" in signal_names or "listening_port_probe_error" in signal_names


def test_factory_unknown_not_supported() -> None:
    collector = get_endpoint_evidence_collector("unknown")
    assert isinstance(collector, UnsupportedPlatformEvidenceCollector)
    bundle = collector.collect_bundle()
    assert bundle.platform_support_level == "NOT_SUPPORTED"
    assert bundle.observations == []
    assert bundle.live_remediation_supported is False
    assert any("NOT_SUPPORTED" in note for note in bundle.limitations)


def test_collect_endpoint_evidence_dict_shape() -> None:
    payload = collect_endpoint_evidence("linux")
    assert payload["platform_support_level"] == "PARTIAL"
    assert "observations" in payload
    assert "limitations" in payload
    assert "collected_at_utc" in payload
    assert "epistemic_note" in payload
    assert "malware" not in payload["epistemic_note"].lower()


def test_non_windows_limitations_never_empty() -> None:
    for family in ("linux", "darwin", "unknown"):
        bundle = get_endpoint_evidence_collector(family).collect_bundle()  # type: ignore[arg-type]
        assert bundle.limitations
        assert bundle.platform_support_level in ("PARTIAL", "NOT_SUPPORTED")
