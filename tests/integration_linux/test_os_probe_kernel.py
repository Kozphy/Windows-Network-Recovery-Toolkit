"""Real Linux kernel integration tests — not collected in default Windows pytest runs.

Run explicitly in Linux CI: ``pytest -q tests/integration_linux``.
"""

from __future__ import annotations

import platform

import pytest

from platform_core.os_probe import detect_linux_distro, is_wsl

pytestmark = [
    pytest.mark.linux_integration,
    pytest.mark.skipif(platform.system().lower() != "linux", reason="Linux kernel integration"),
]


def test_wsl_flag_and_distro_on_linux_kernel() -> None:
    assert isinstance(is_wsl(), bool)
    assert detect_linux_distro() in {"ubuntu", "debian", "wsl", "unknown"}
