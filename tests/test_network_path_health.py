"""Tests for dual-stack network path health and Prefer-IPv4 gating."""

from __future__ import annotations

from pathlib import Path

from src.proxy_drift.network_path_health import (
    CONFIRM_PREFER_IPV4,
    assess_network_path,
    run_network_path_health,
)


def _probe(v4_ok: bool, v6_ok: bool) -> dict:
    return {
        "youtube_204": {
            "url": "https://www.youtube.com/generate_204",
            "v4": {"ok": v4_ok, "http_code": 204 if v4_ok else 0, "time_s": 0.1, "error": None},
            "v6": {"ok": v6_ok, "http_code": 204 if v6_ok else 0, "time_s": 0.05, "error": None},
            "default": {
                "ok": v4_ok,
                "http_code": 204 if v4_ok else 0,
                "time_s": 0.1,
                "error": None,
            },
        }
    }


def test_detect_broken_ipv6_ipv4_ok() -> None:
    out = assess_network_path(
        probes=_probe(True, False),
        wifi_ipv6_enabled=True,
        prefer_ipv4_set=False,
        proxy_enable=0,
    )
    assert out["classification"] == "IPV6_BROKEN_IPV4_OK"
    assert out["match_broken_ipv6"] is True


def test_mitigated_when_prefer_ipv4_and_wifi_v6_off() -> None:
    out = assess_network_path(
        probes=_probe(True, False),
        wifi_ipv6_enabled=False,
        prefer_ipv4_set=True,
        proxy_enable=0,
    )
    assert out["classification"] == "IPV6_BROKEN_MITIGATED"
    assert out["mitigated"] is True


def test_path_ok_when_v6_works() -> None:
    out = assess_network_path(
        probes=_probe(True, True),
        wifi_ipv6_enabled=True,
        prefer_ipv4_set=False,
        proxy_enable=0,
    )
    assert out["classification"] == "PATH_OK"


def test_preview_default(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(**_k):
        applied.append("x")
        return {"steps": [], "errors": []}

    out = run_network_path_health(
        dry_run=True,
        confirm="",
        repo_root=tmp_path,
        probes=_probe(True, False),
        wifi_ipv6_enabled=True,
        prefer_ipv4_set=False,
        proxy_enable=0,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "preview_only"
    assert applied == []


def test_blocked_without_token(tmp_path: Path) -> None:
    applied: list[str] = []

    def _apply(**_k):
        applied.append("x")
        return {"steps": ["ok"], "errors": []}

    out = run_network_path_health(
        dry_run=False,
        confirm="WRONG",
        repo_root=tmp_path,
        probes=_probe(True, False),
        wifi_ipv6_enabled=True,
        prefer_ipv4_set=False,
        proxy_enable=0,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "blocked"
    assert applied == []


def test_partial_when_wsl_ipv6_left() -> None:
    out = assess_network_path(
        probes=_probe(True, False),
        wifi_ipv6_enabled=False,
        prefer_ipv4_set=True,
        proxy_enable=0,
        ipv6_enabled_adapters=["vEthernet (WSL (Hyper-V firewall))"],
    )
    assert out["classification"] == "IPV6_PARTIAL_MITIGATION"


def test_happy_eyeballs_stall() -> None:
    probes = {
        "microsoft": {
            "url": "https://www.microsoft.com",
            "v4": {"ok": True, "http_code": 200, "time_s": 0.2, "error": None},
            "v6": {"ok": False, "http_code": 0, "time_s": 0.05, "error": None},
            "default": {"ok": False, "http_code": 0, "time_s": 8.0, "error": None},
        }
    }
    out = assess_network_path(
        probes=probes,
        wifi_ipv6_enabled=False,
        prefer_ipv4_set=True,
        proxy_enable=0,
        ipv6_enabled_adapters=[],
    )
    assert out["classification"] == "HAPPY_EYEBALLS_STALL"
    assert out["happy_eyeballs_stall"] is True


def test_apply_with_token(tmp_path: Path) -> None:
    def _apply(*, interface, run, all_adapters=True):
        assert interface == "Wi-Fi"
        assert all_adapters is True
        return {"steps": ["Prefer IPv4"], "errors": []}

    out = run_network_path_health(
        dry_run=False,
        confirm=CONFIRM_PREFER_IPV4,
        repo_root=tmp_path,
        probes=_probe(True, False),
        wifi_ipv6_enabled=True,
        prefer_ipv4_set=False,
        proxy_enable=0,
        apply_fn=_apply,
        audit_path=tmp_path / "a.jsonl",
    )
    assert out["action_taken"] == "remediated"
