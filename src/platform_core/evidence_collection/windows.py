"""Windows endpoint evidence collector — FULL platform support."""

from __future__ import annotations

from typing import Any

from platform_core.network_diagnostics.windows import WindowsNetworkDiagnostics
from src.platform_core.evidence_collection.base import EndpointEvidenceCollector
from src.platform_core.evidence_collection.models import OsFamily, PlatformSupportLevel


class WindowsEndpointEvidenceCollector(EndpointEvidenceCollector):
    """Delegates to existing Windows network diagnostics — WinINET/WinHTTP observation tier."""

    def __init__(self, provider: WindowsNetworkDiagnostics | None = None) -> None:
        self._provider = provider or WindowsNetworkDiagnostics()

    @property
    def collector_id(self) -> str:
        return "windows_network_diagnostics_v1"

    def os_family(self) -> OsFamily:
        return "windows"

    def platform_support_level(self) -> PlatformSupportLevel:
        return "FULL"

    def limitations(self) -> list[str]:
        return list(self._provider.limitations())

    def live_remediation_supported(self) -> bool:
        return bool(self._provider.live_remediation_supported())

    def collect_observations(self) -> list[dict[str, Any]]:
        return list(self._provider.collect_observations())
