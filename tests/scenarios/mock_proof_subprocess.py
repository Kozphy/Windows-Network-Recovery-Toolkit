"""Reusable ``subprocess.run`` fakes for localhost proxy proof tests — no real network."""

from __future__ import annotations

from collections.abc import Callable
from subprocess import CompletedProcess


def localhost_proxy_proof_subprocess(
    *,
    proxy_curl_rc: int,
    proxy_curl_out: str,
    bypass_curl_rc: int,
    bypass_curl_out: str,
) -> Callable[..., CompletedProcess]:
    """Build ``subprocess.run`` injector for :func:`src.proof.proxy_https.run_localhost_proxy_https_proof`."""

    def _run(argv: list[str], **_kwargs: object) -> CompletedProcess:
        av = list(argv)
        if av[:2] == ["curl", "--version"]:
            return CompletedProcess(av, 0, "curl 8.0 deterministic\n", "")
        if "-x" in av:
            return CompletedProcess(av, proxy_curl_rc, proxy_curl_out, "")
        if "--noproxy" in av:
            return CompletedProcess(av, bypass_curl_rc, bypass_curl_out, "")
        if av[:2] == ["netsh", "winhttp"]:
            return CompletedProcess(av, 0, "Direct access (no proxy server).\n", "")
        if av[:2] == ["netstat", "-an"]:
            return CompletedProcess(
                av,
                0,
                "TCP    127.0.0.1:9999         0.0.0.0:0              LISTENING\n",
                "",
            )
        return CompletedProcess(av, 0, "", "")

    return _run
