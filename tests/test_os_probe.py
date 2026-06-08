from __future__ import annotations

import platform
from pathlib import Path
from unittest.mock import patch

import pytest

from platform_core.network_diagnostics import base as nd_base
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


@pytest.mark.parametrize(
    ("system_name", "proc_version", "os_release", "expect_wsl", "expect_distro"),
    [
        ("Windows", None, None, False, "unknown"),
        ("Darwin", None, None, False, "unknown"),
        ("Linux", "Linux version 6.1.0 microsoft-standard-WSL2", "ID=ubuntu\n", True, "wsl"),
        ("Linux", "Linux version 6.1.0-generic", "ID=ubuntu\nVERSION_ID=22.04\n", False, "ubuntu"),
        ("Linux", "Linux version 6.1.0-generic", "ID=debian\nVERSION_ID=12\n", False, "debian"),
        ("Linux", "Linux version 6.1.0-generic", "ID=fedora\n", False, "unknown"),
        ("Linux", None, None, False, "unknown"),
    ],
)
def test_wsl_and_linux_distro_platform_branches(
    monkeypatch: pytest.MonkeyPatch,
    system_name: str,
    proc_version: str | None,
    os_release: str | None,
    expect_wsl: bool,
    expect_distro: str,
) -> None:
    """Exercise is_wsl / detect_linux_distro branches without requiring a Linux host."""

    monkeypatch.setattr(nd_base.platform, "system", lambda: system_name)
    real_read_text = Path.read_text

    def _read_text(self: Path, *args: object, **kwargs: object) -> str:
        p = self.as_posix().replace("\\", "/")
        if p == "/proc/version":
            if proc_version is None:
                raise OSError("missing /proc/version")
            return proc_version
        if p == "/etc/os-release":
            if os_release is None:
                raise OSError("missing /etc/os-release")
            return os_release
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text)

    assert isinstance(is_wsl(), bool)
    assert is_wsl() is expect_wsl
    assert detect_linux_distro() == expect_distro


@pytest.mark.parametrize("system_name", ["Windows", "Linux", "Darwin", "FreeBSD"])
def test_detect_os_family_mocked_platform_system(system_name: str) -> None:
    with patch.object(nd_base.platform, "system", return_value=system_name):
        family = nd_base.detect_os_family()
    if system_name == "Windows":
        assert family == "windows"
    elif system_name == "Linux":
        assert family == "linux"
    elif system_name == "Darwin":
        assert family == "darwin"
    else:
        assert family == "unknown"
