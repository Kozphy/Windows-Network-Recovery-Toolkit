"""Docker demo stack contract tests — no Docker daemon required."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from windows_network_toolkit.proxy_remediation import run_proxy_disable
from windows_network_toolkit.safety import is_blocked_action, is_demo_mode

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_compose_full_stack_unchanged() -> None:
    text = _read("docker-compose.yml")
    assert "  api:" in text
    assert "  postgres:" in text
    assert "  prometheus:" in text
    assert "  grafana:" in text


def test_compose_demo_exists_with_demo_mode() -> None:
    text = _read("docker-compose.demo.yml")
    assert "DEMO_MODE" in text
    assert 'DEMO_MODE: "true"' in text or "DEMO_MODE: 'true'" in text
    assert "./fixtures:/app/fixtures:ro" in text
    assert "./demo-output:/app/demo-output" in text
    assert "postgres:" not in text
    assert "prometheus:" not in text
    assert "grafana:" not in text


def test_demo_mode_forces_dry_run_proxy_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    assert is_demo_mode()
    result = run_proxy_disable(dry_run=False, confirm="DISABLE_WININET_PROXY")
    assert result.get("dry_run") is True or result.get("policy", {}).get("dry_run") is True or "unsupported" in str(result).lower() or result.get("result", {}).get("dry_run") is True


def test_demo_mode_blocks_all_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "1")
    assert is_blocked_action("DISABLE_WININET_PROXY")
    assert is_blocked_action("KILL_PROXY_PROCESS")


def test_health_returns_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "yes")
    client = TestClient(app)
    r = client.get("/health")
    assert r.json()["mode"] == "demo"


def test_root_redirects_to_openapi_docs() -> None:
    client = TestClient(app)
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/docs"


def test_favicon_returns_no_content() -> None:
    client = TestClient(app)
    assert client.get("/favicon.ico").status_code == 204


def test_readme_contains_reviewer_docker_demo_section() -> None:
    readme = _read("README.md")
    assert "Reviewer Docker Demo" in readme or "docker-compose.demo.yml" in readme
