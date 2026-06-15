"""Browser vs request path comparison for URL diagnostics."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from windows_network_toolkit.collectors.proxy_registry_collector import collect_proxy_registry

from .http_probe import probe_http_browser_ua
from .models import BrowserCompareObservation, HttpObservation, ProbeStatus


def _collect_winhttp(*, run: Callable[..., Any] | None, timeout: float) -> dict[str, Any]:
    if run is None:
        return {"direct_access": True, "raw": ""}
    code, out = 0, ""
    try:
        proc = run(
            ["netsh", "winhttp", "show", "proxy"],
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    except OSError:
        pass
    lower = out.lower()
    return {
        "direct_access": "direct access" in lower and "no proxy server" in lower,
        "raw": out[:400],
    }


def compare_browser_paths(
    url: str,
    http: HttpObservation,
    *,
    run: Callable[..., Any] | None = None,
    timeout: float = 10.0,
    inject: dict[str, Any] | None = None,
    browser_ua_result: bool | None = None,
) -> BrowserCompareObservation:
    if inject is not None:
        return BrowserCompareObservation.model_validate(inject)

    wininet = collect_proxy_registry(run=run)
    winhttp = _collect_winhttp(run=run, timeout=timeout)
    proxy_on = int(wininet.get("proxy_enable") or 0) == 1
    proxy_server = str(wininet.get("proxy_server") or "")

    request_ok = http.status == ProbeStatus.OK and http.status_code is not None
    ua_ok = browser_ua_result
    if ua_ok is None:
        ua_ok = probe_http_browser_ua(url, timeout=timeout)

    mismatches: list[str] = []
    loopback = "127.0.0.1" in proxy_server or "localhost" in proxy_server.lower()
    if request_ok and proxy_on and loopback:
        mismatches.append("request_succeeds_but_wininet_localhost_proxy_enabled")
    if request_ok and not ua_ok:
        mismatches.append("python_request_succeeds_but_browser_ua_failed")
    env_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or ""
    env_https = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    if request_ok and env_proxy and loopback:
        mismatches.append("env_proxy_set_with_localhost")

    return BrowserCompareObservation(
        wininet_proxy_enabled=proxy_on,
        wininet_proxy_server=proxy_server,
        winhttp_direct_access=bool(winhttp.get("direct_access")),
        env_http_proxy=env_proxy,
        env_https_proxy=env_https,
        request_succeeded=request_ok,
        browser_ua_succeeded=ua_ok,
        mismatches=mismatches,
    )
