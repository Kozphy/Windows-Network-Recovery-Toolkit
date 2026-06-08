"""Contract tests for docker-compose platform stack (no Docker daemon required)."""

from __future__ import annotations

from pathlib import Path


def _compose_text() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "docker-compose.yml").read_text(encoding="utf-8")


def test_compose_declares_api_prometheus_grafana() -> None:
    text = _compose_text()
    assert "  api:" in text
    assert "  prometheus:" in text
    assert "  grafana:" in text


def test_api_healthcheck_targets_platform_health() -> None:
    assert "/platform/health" in _compose_text()


def test_api_fixture_mode_and_safe_mode() -> None:
    text = _compose_text()
    assert "PLATFORM_SAFE_MODE" in text
    assert "PLATFORM_FIXTURE_MODE" in text
