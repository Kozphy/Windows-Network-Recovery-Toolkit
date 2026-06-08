from __future__ import annotations

import platform

import pytest

from platform_core.network_diagnostics import get_network_diagnostics
from platform_core.network_diagnostics.linux import LinuxNetworkDiagnostics
from platform_core.network_diagnostics.windows import WindowsNetworkDiagnostics


def test_get_network_diagnostics_provider_type() -> None:
    provider = get_network_diagnostics()
    system = platform.system().lower()
    if system == "windows":
        assert isinstance(provider, WindowsNetworkDiagnostics)
    elif system == "linux":
        assert isinstance(provider, LinuxNetworkDiagnostics)


def test_platform_payload_includes_epistemic_note() -> None:
    payload = get_network_diagnostics().platform_payload()
    assert "observations" in payload
    assert "epistemic_note" in payload
    assert payload["live_remediation_supported"] == (platform.system().lower() == "windows")


def test_linux_provider_observe_only() -> None:
    provider = LinuxNetworkDiagnostics()
    assert provider.live_remediation_supported() is False
    assert any("observe-only" in note.lower() for note in provider.limitations())


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows proxy probes")
def test_windows_provider_includes_proxy_observations() -> None:
    provider = WindowsNetworkDiagnostics()
    names = {row["signal_name"] for row in provider.collect_observations()}
    assert "proxy_enable" in names or "windows_proxy_probe_error" in names
