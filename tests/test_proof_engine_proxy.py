from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from src.core.models import ProxyRegistrySnapshot
from src.proof.contracts import ProofStatus
from src.proof.proxy_https import (
    _interpret_curl_https_ok,
    _listening_on_port_windows,
    _winhttp_hints_localhost,
    run_localhost_proxy_https_proof,
)


def test_interpret_curl_https_ok() -> None:
    assert _interpret_curl_https_ok(0, "200") is True
    assert _interpret_curl_https_ok(0, "302") is True
    assert _interpret_curl_https_ok(0, "600") is False
    assert _interpret_curl_https_ok(1, "200") is False
    assert _interpret_curl_https_ok(0, "abc") is False


def test_listening_on_port_windows() -> None:
    body = "TCP    127.0.0.1:9999         0.0.0.0:0              LISTENING\n"
    assert _listening_on_port_windows(body, 9999) is True
    assert _listening_on_port_windows(body, 8888) is False


def test_winhttp_hints_localhost() -> None:
    ok, port = _winhttp_hints_localhost(
        "Current WinHTTP proxy settings:\n    Proxy Server(s) : 127.0.0.1:9797\n"
    )
    assert ok is True
    assert port == 9797
    ok2, p2 = _winhttp_hints_localhost("Direct access (no proxy server).")
    assert ok2 is False and p2 is None


def _fake_subprocess_run(argv: list[str], **_kwargs: object) -> CompletedProcess:
    av = list(argv)
    if av[:2] == ["netsh", "winhttp"]:
        return CompletedProcess(av, 0, "Direct access (no proxy server).\n", "")
    if av[:2] == ["netstat", "-an"]:
        return CompletedProcess(
            av,
            0,
            "TCP    127.0.0.1:9999         0.0.0.0:0              LISTENING\n",
            "",
        )
    if av[:2] == ["curl", "--version"]:
        return CompletedProcess(av, 0, "curl 8.0.0 (Windows)\n", "")
    if "-x" in av and "http://127.0.0.1:9999" in av:
        return CompletedProcess(av, 7, "", "connection refused")
    if "--noproxy" in av:
        return CompletedProcess(av, 0, "302", "")
    return CompletedProcess(av, 99, "", f"unexpected argv={av!r}")


@pytest.mark.parametrize(
    ("expect_status", "proxy_rc", "proxy_out", "bypass_rc", "bypass_out"),
    [
        (ProofStatus.CONFIRMED, 7, "", 0, "302"),
        (ProofStatus.REJECTED, 0, "200", 0, "200"),
        (ProofStatus.INCONCLUSIVE, 7, "", 7, ""),
    ],
)
def test_https_contrast_statuses(
    expect_status: ProofStatus,
    proxy_rc: int,
    proxy_out: str,
    bypass_rc: int,
    bypass_out: str,
) -> None:
    snap = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:9999",
        auto_config_url=None,
        auto_detect=0,
    )

    def run_side_effect(argv: list[str], **_kwargs: object) -> CompletedProcess:
        av = list(argv)
        if av[:2] == ["curl", "--version"]:
            return CompletedProcess(av, 0, "curl\n", "")
        if "-x" in av:
            return CompletedProcess(av, proxy_rc, proxy_out, "")
        if "--noproxy" in av:
            return CompletedProcess(av, bypass_rc, bypass_out, "")
        return _fake_subprocess_run(av)

    with patch("src.proof.proxy_https.read_proxy_registry", return_value=snap):
        result = run_localhost_proxy_https_proof(
            subprocess_run=run_side_effect,
            curl_timeout=4.0,
            net_timeout=5.0,
            reg_timeout=5.0,
        )
    assert result.status == expect_status
    assert result.proof_id == "localhost_proxy_https_contrast"


def test_no_proxy_url_inconclusive() -> None:
    snap = ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="corp-proxy.example.int:8080",
        auto_config_url=None,
        auto_detect=0,
    )

    def run_side_effect(argv: list[str], **_kwargs: object) -> CompletedProcess:
        if argv[:2] == ["curl", "--version"]:
            return CompletedProcess(list(argv), 0, "curl\n", "")
        return _fake_subprocess_run(argv)

    with patch("src.proof.proxy_https.read_proxy_registry", return_value=snap):
        r = run_localhost_proxy_https_proof(subprocess_run=run_side_effect)
    assert r.status == ProofStatus.INCONCLUSIVE
    assert "Could not derive" in r.summary
