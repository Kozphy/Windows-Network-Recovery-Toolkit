from __future__ import annotations

import platform

import pytest

from platform_core.os_probe import (
    collect_linux_network_observations,
    collect_platform_observations,
    detect_linux_distro,
    detect_os_family,
    is_wsl,
)


def test_detect_os_family_returns_known_literal() -> None:
    family = detect_os_family()
    assert family in {"windows", "linux", "darwin", "unknown"}


def test_linux_observations_include_os_family() -> None:
    obs = collect_linux_network_observations()
    names = {row["signal_name"] for row in obs}
    assert "os_family" in names
    if platform.system().lower() == "linux":
        assert "linux_distro" in names


def test_collect_platform_observations_shape() -> None:
    payload = collect_platform_observations()
    assert "os_family" in payload
    assert "observations" in payload
    assert isinstance(payload["observations"], list)
    if detect_os_family() == "linux":
        assert payload["live_remediation_supported"] is False


@pytest.mark.skipif(platform.system().lower() != "linux", reason="WSL detection requires Linux")
def test_wsl_flag_is_boolean_on_linux() -> None:
    assert isinstance(is_wsl(), bool)
    assert detect_linux_distro() in {"ubuntu", "debian", "wsl", "unknown"}
