"""Shared pytest fixtures for the deterministic (fixture-driven) test suite."""

from __future__ import annotations

import platform

import pytest


@pytest.fixture
def simulated_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report the host as Windows so Windows-only surfaces stay covered on Linux CI.

    Only the platform guard is simulated; every Windows API call still has to be
    mocked or fixture-driven by the test itself.
    """
    monkeypatch.setattr(platform, "system", lambda: "Windows")
