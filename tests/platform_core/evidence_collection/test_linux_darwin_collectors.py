"""Collector behavior tests for Linux/macOS foundation paths."""

from __future__ import annotations

from unittest.mock import patch

from platform_core.network_diagnostics.darwin import (
    DarwinNetworkDiagnostics,
    collect_networksetup_proxy_hints,
)
from platform_core.network_diagnostics.listeners import _parse_ss_or_netstat, probe_listening_ports
from src.platform_core.evidence_collection.darwin import DarwinEndpointEvidenceCollector
from src.platform_core.evidence_collection.linux import LinuxEndpointEvidenceCollector


def test_linux_collector_includes_listening_port_signals() -> None:
    with patch(
        "platform_core.network_diagnostics.listeners.probe_listening_ports",
        return_value={
            "available": True,
            "source": "ss",
            "listener_count": 3,
            "localhost_listener_count": 1,
            "common_proxy_ports": [3128],
        },
    ):
        bundle = LinuxEndpointEvidenceCollector().collect_bundle()
    signals = {row["signal_name"] for row in bundle.observations}
    assert "listening_port_probe_available" in signals
    assert bundle.platform_support_level == "PARTIAL"
    assert bundle.live_remediation_supported is False
    assert any("WinINET" in note or "wininet" in note.lower() for note in bundle.limitations)


def test_darwin_collector_delegates_to_network_diagnostics() -> None:
    with patch(
        "platform_core.network_diagnostics.darwin.collect_networksetup_proxy_hints",
        return_value=[
            {
                "signal_name": "networksetup_available",
                "value": True,
                "source": "network_diagnostics.darwin",
            }
        ],
    ), patch(
        "platform_core.network_diagnostics.darwin.listening_port_observations",
        return_value=[
            {
                "signal_name": "listening_port_probe_available",
                "value": False,
                "source": "network_diagnostics.darwin",
            }
        ],
    ):
        bundle = DarwinEndpointEvidenceCollector().collect_bundle()
    assert bundle.collector_id == "darwin_network_diagnostics_v1"
    assert bundle.platform_support_level == "PARTIAL"
    signals = {row["signal_name"] for row in bundle.observations}
    assert "networksetup_available" in signals
    assert "proxy_enable" not in signals
    assert "winhttp_proxy_state" not in signals


def test_networksetup_hints_when_unavailable() -> None:
    with patch("platform_core.network_diagnostics.darwin.shutil.which", return_value=None):
        rows = collect_networksetup_proxy_hints()
    assert rows[0]["signal_name"] == "networksetup_available"
    assert rows[0]["value"] is False


def test_networksetup_parses_web_proxy_block() -> None:
    def fake_run(args: list[str], **kwargs: object) -> tuple[int, str]:
        if args == ["-listallnetworkservices"]:
            return 0, "Wi-Fi\nAn asterisk (*) denotes that a network service is disabled.\n"
        if args == ["-getwebproxy", "Wi-Fi"]:
            return 0, "Enabled: Yes\nServer: 127.0.0.1\nPort: 8888\n"
        if args == ["-getsecurewebproxy", "Wi-Fi"]:
            return 0, "Enabled: No\nServer: \nPort: 0\n"
        return 1, ""

    with patch("platform_core.network_diagnostics.darwin.shutil.which", return_value="/usr/sbin/networksetup"), patch(
        "platform_core.network_diagnostics.darwin._run_networksetup",
        side_effect=fake_run,
    ):
        rows = collect_networksetup_proxy_hints()
    by_name = {row["signal_name"]: row["value"] for row in rows}
    assert by_name["networksetup_available"] is True
    assert by_name["networksetup_web_proxy_enabled"] is True
    assert by_name["networksetup_web_proxy_endpoint"] == "127.0.0.1:8888"


def test_parse_ss_listening_lines() -> None:
    sample = "State  Recv-Q Send-Q Local Address:Port Peer Address:Port\nLISTEN 0 128 127.0.0.1:8080 0.0.0.0:*\n"
    listeners = _parse_ss_or_netstat(sample)
    assert listeners == [{"address": "127.0.0.1", "port": 8080}]


def test_probe_listening_ports_never_raises() -> None:
    with patch("platform_core.network_diagnostics.listeners.shutil.which", return_value=None):
        result = probe_listening_ports()
    assert result["available"] is False


def test_darwin_provider_collect_never_raises() -> None:
    with patch("platform_core.network_diagnostics.darwin.shutil.which", return_value=None):
        rows = DarwinNetworkDiagnostics().collect_observations()
    assert any(row["signal_name"] == "os_family" for row in rows)
