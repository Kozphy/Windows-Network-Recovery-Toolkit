"""Read-only proxy config audit: missing tools, configured values, env vars, drift findings."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from proxy_guard.proxy_config_audit import (
    ProxyConfigCheckResult,
    build_proxy_config_audit,
    classify_findings,
    collect_environment_proxies,
    collect_git_proxy,
    collect_npm_proxy,
)


def _fake_run(scripted: dict[tuple[str, ...], tuple[int, str, str]]) -> Callable[..., Any]:
    """Build a fake subprocess.run that returns scripted ``(rc, stdout, stderr)`` per argv tuple."""

    def runner(argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        key = tuple(argv)
        rc, stdout, stderr = scripted.get(key, (1, "", "no scripted response"))
        return SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)

    return runner


def test_missing_git_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("proxy_guard.proxy_config_audit._which", lambda exe: None)
    result = collect_git_proxy(run=_fake_run({}))
    assert result["available"] is False
    assert result["values"] == {"http.proxy": None, "https.proxy": None}
    assert any("git" in note for note in result["limitations"])


def test_missing_npm_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("proxy_guard.proxy_config_audit._which", lambda exe: None)
    result = collect_npm_proxy(run=_fake_run({}))
    assert result["available"] is False
    assert result["values"] == {"proxy": None, "https-proxy": None, "registry": None}


def test_configured_git_and_npm_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("proxy_guard.proxy_config_audit._which", lambda exe: f"/usr/bin/{exe.replace('.cmd', '')}")
    git_run = _fake_run(
        {
            ("/usr/bin/git", "config", "--global", "--get", "http.proxy"): (0, "http://proxy.local:3128\n", ""),
            ("/usr/bin/git", "config", "--global", "--get", "https.proxy"): (1, "", ""),
        }
    )
    npm_run = _fake_run(
        {
            ("/usr/bin/npm", "config", "get", "proxy"): (0, "null\n", ""),
            ("/usr/bin/npm", "config", "get", "https-proxy"): (0, "http://proxy.local:3128\n", ""),
            ("/usr/bin/npm", "config", "get", "registry"): (0, "https://registry.npmjs.org/\n", ""),
        }
    )
    git = collect_git_proxy(run=git_run)
    npm = collect_npm_proxy(run=npm_run)
    assert git["values"]["http.proxy"] == "http://proxy.local:3128"
    assert git["values"]["https.proxy"] is None
    assert npm["values"]["proxy"] is None
    assert npm["values"]["https-proxy"] == "http://proxy.local:3128"
    assert npm["values"]["registry"] == "https://registry.npmjs.org/"


def test_environment_variables_are_reported() -> None:
    env = {
        "HTTPS_PROXY": "http://proxy.local:3128",
        "NO_PROXY": "localhost,127.0.0.1",
        "PATH": "/usr/bin",
    }
    out = collect_environment_proxies(env=env)
    assert out["HTTPS_PROXY"] == "http://proxy.local:3128"
    assert out["NO_PROXY"] == "localhost,127.0.0.1"
    assert out["HTTP_PROXY"] is None


def test_classify_findings_emits_npm_drift_and_browser_policy_when_localhost_proxy() -> None:
    checks = {
        "wininet": {"available": True, "values": {"ProxyEnable": 0, "ProxyServer": "", "AutoConfigURL": None, "ProxyOverride": None}},
        "winhttp": {"available": True, "direct_access": True, "raw": "Direct access (no proxy server)."},
        "git": {"available": True, "values": {"http.proxy": None, "https.proxy": None}},
        "npm": {"available": True, "values": {"proxy": None, "https-proxy": "http://proxy.local:3128", "registry": None}},
        "environment": {"HTTPS_PROXY": "http://proxy.local:3128", "HTTP_PROXY": None},
        "browser_policy": {"available": True, "values": {"chrome_user": "PROXY 127.0.0.1:8888"}},
    }
    findings = classify_findings(checks)
    kinds = {f.kind for f in findings}
    assert "npm_proxy_drift" in kinds
    assert "env_proxy_drift" in kinds
    assert "browser_policy_proxy" in kinds


def test_classify_findings_detects_wininet_winhttp_mismatch_and_localhost_drift() -> None:
    checks = {
        "wininet": {
            "available": True,
            "values": {
                "ProxyEnable": 1,
                "ProxyServer": "127.0.0.1:54321",
                "AutoConfigURL": None,
                "ProxyOverride": None,
            },
        },
        "winhttp": {"available": True, "direct_access": True, "raw": "Direct access."},
        "git": {"available": True, "values": {"http.proxy": None, "https.proxy": None}},
        "npm": {"available": True, "values": {"proxy": None, "https-proxy": None, "registry": None}},
        "environment": {},
        "browser_policy": {"available": True, "values": {"chrome_user": None, "edge_user": None}},
    }
    findings = classify_findings(checks)
    kinds = {f.kind for f in findings}
    assert "windows_proxy_drift" in kinds
    assert "wininet_winhttp_mismatch" in kinds


def test_build_proxy_config_audit_returns_typed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("proxy_guard.proxy_config_audit._which", lambda exe: None)
    monkeypatch.setattr(
        "proxy_guard.proxy_config_audit.collect_wininet_proxy",
        lambda: {"available": True, "values": {"ProxyEnable": 0, "ProxyServer": "", "AutoConfigURL": None, "ProxyOverride": None}, "limitations": []},
    )
    monkeypatch.setattr(
        "proxy_guard.proxy_config_audit.collect_winhttp_proxy",
        lambda *, run=None: {"available": False, "raw": "", "direct_access": None, "limitations": ["non-windows"]},
    )
    monkeypatch.setattr(
        "proxy_guard.proxy_config_audit.collect_browser_policy_proxy",
        lambda *, run=None: {"available": False, "values": {"chrome_user": None}, "limitations": []},
    )
    result = build_proxy_config_audit(run=_fake_run({}), env={"HTTPS_PROXY": "http://example:3128"})
    assert isinstance(result, ProxyConfigCheckResult)
    payload = result.to_dict()
    assert "proxy_config_checks" in payload
    assert "findings" in payload
    assert any(f["kind"] == "env_proxy_drift" for f in payload["findings"])
