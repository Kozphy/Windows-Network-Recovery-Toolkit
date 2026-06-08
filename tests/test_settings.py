from __future__ import annotations

import pytest

from platform_core.settings import PlatformSettings, reset_settings_cache


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache()
    monkeypatch.delenv("PLATFORM_DATA_DIR", raising=False)
    monkeypatch.delenv("PLATFORM_SAFE_MODE", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)


def test_settings_default_safe_mode() -> None:
    reset_settings_cache()
    settings = PlatformSettings()
    assert settings.platform_safe_mode is True


def test_settings_parses_safe_mode_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATFORM_SAFE_MODE", "0")
    reset_settings_cache()
    settings = PlatformSettings()
    assert settings.platform_safe_mode is False


def test_settings_cors_origins_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://a,http://b")
    reset_settings_cache()
    settings = PlatformSettings()
    assert settings.cors_origins_list() == ["http://a", "http://b"]


def test_settings_sync_process_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("PLATFORM_DATA_DIR", str(tmp_path))
    reset_settings_cache()
    settings = PlatformSettings()
    settings.sync_process_env()
    import os

    assert os.environ["PLATFORM_DATA_DIR"] == str(tmp_path.resolve())
