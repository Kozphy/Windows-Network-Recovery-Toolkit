from __future__ import annotations

import importlib


def _reload_tracing(monkeypatch, *, enabled: str | None, connection_string: str | None):
    if enabled is None:
        monkeypatch.delenv("WNRT_AZURE_MONITOR_ENABLED", raising=False)
    else:
        monkeypatch.setenv("WNRT_AZURE_MONITOR_ENABLED", enabled)

    if connection_string is None:
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    else:
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", connection_string)

    import backend.tracing as tracing

    return importlib.reload(tracing)


def test_azure_monitor_is_opt_in(monkeypatch):
    tracing = _reload_tracing(
        monkeypatch,
        enabled=None,
        connection_string="InstrumentationKey=not-a-real-key",
    )

    assert tracing._env_flag("WNRT_AZURE_MONITOR_ENABLED") is False
    assert tracing._configure_azure_monitor() is False
    assert tracing.azure_monitor_configured() is False


def test_azure_monitor_requires_connection_string(monkeypatch):
    tracing = _reload_tracing(monkeypatch, enabled="1", connection_string=None)

    assert tracing._env_flag("WNRT_AZURE_MONITOR_ENABLED") is True
    assert tracing._configure_azure_monitor() is False
    assert tracing.azure_monitor_configured() is False


def test_false_like_flag_values_stay_disabled(monkeypatch):
    tracing = _reload_tracing(
        monkeypatch,
        enabled="false",
        connection_string="InstrumentationKey=not-a-real-key",
    )

    assert tracing._env_flag("WNRT_AZURE_MONITOR_ENABLED") is False
    assert tracing._configure_azure_monitor() is False
