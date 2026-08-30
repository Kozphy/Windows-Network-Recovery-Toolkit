"""HTTP-layer probes for localhost targets (direct vs proxy-aware)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from .target import filter_response_headers


@dataclass
class HttpProbeResult:
    mode: str  # direct | proxy_aware
    requested_url: str
    effective_url: str | None = None
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    redirect_chain: list[str] = field(default_factory=list)
    tls_info: dict[str, Any] | None = None
    exception_category: str | None = None
    detail: str = ""
    success: bool = False
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "requested_url": self.requested_url,
            "effective_url": self.effective_url,
            "status_code": self.status_code,
            "response_headers": dict(self.response_headers),
            "elapsed_ms": round(self.elapsed_ms, 3),
            "redirect_chain": list(self.redirect_chain),
            "tls_info": self.tls_info,
            "exception_category": self.exception_category,
            "detail": self.detail,
            "success": self.success,
            "timestamp_utc": self.timestamp_utc,
        }


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _categorize_http_exc(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP_ERROR"
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ConnectionRefusedError) or "refused" in str(exc).lower():
            return "CONNECTION_REFUSED"
        if isinstance(reason, TimeoutError) or "timed out" in str(exc).lower():
            return "TIMEOUT"
        return "URL_ERROR"
    if isinstance(exc, ConnectionRefusedError):
        return "CONNECTION_REFUSED"
    if isinstance(exc, OSError):
        return "OS_ERROR"
    return "UNKNOWN"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def http_probe_direct(url: str, *, timeout: float = 2.0) -> HttpProbeResult:
    """GET *url* with proxies explicitly disabled. Does not store response bodies."""

    result = HttpProbeResult(mode="direct", requested_url=url, timestamp_utc=_now())
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirect,
        )
        with opener.open(req, timeout=timeout) as resp:
            result.elapsed_ms = (time.perf_counter() - start) * 1000.0
            result.status_code = int(resp.status)
            result.effective_url = str(resp.geturl())
            result.response_headers = filter_response_headers({k: v for k, v in resp.headers.items()})
            result.success = 200 <= result.status_code < 500
            result.detail = f"Direct GET status={result.status_code}"
            if urlparse(url).scheme == "https":
                result.tls_info = {"scheme": "https", "note": "TLS negotiated; certificate details not collected by default."}
            return result
    except urllib.error.HTTPError as exc:
        result.elapsed_ms = (time.perf_counter() - start) * 1000.0
        result.status_code = int(exc.code)
        result.exception_category = "HTTP_ERROR"
        result.detail = f"HTTPError {exc.code}"
        # 3xx from no-redirect handler surfaces here sometimes
        result.success = 200 <= result.status_code < 500
        if exc.headers:
            result.response_headers = filter_response_headers({k: v for k, v in exc.headers.items()})
        return result
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        result.elapsed_ms = (time.perf_counter() - start) * 1000.0
        result.exception_category = _categorize_http_exc(exc)
        result.detail = str(exc)[:300]
        return result


def http_probe_proxy_aware(
    url: str,
    *,
    timeout: float = 2.0,
    proxy_url: str | None = None,
) -> HttpProbeResult:
    """GET *url* using system proxy env / explicit proxy when provided."""

    result = HttpProbeResult(mode="proxy_aware", requested_url=url, timestamp_utc=_now())
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        if proxy_url:
            handlers = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            opener = urllib.request.build_opener(handlers, _NoRedirect)
        else:
            # Default opener honors environment / system proxy settings where available
            opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=timeout) as resp:
            result.elapsed_ms = (time.perf_counter() - start) * 1000.0
            result.status_code = int(resp.status)
            result.effective_url = str(resp.geturl())
            result.response_headers = filter_response_headers({k: v for k, v in resp.headers.items()})
            result.success = 200 <= result.status_code < 500
            result.detail = f"Proxy-aware GET status={result.status_code}"
            return result
    except urllib.error.HTTPError as exc:
        result.elapsed_ms = (time.perf_counter() - start) * 1000.0
        result.status_code = int(exc.code)
        result.exception_category = "HTTP_ERROR"
        result.detail = f"HTTPError {exc.code}"
        result.success = 200 <= result.status_code < 500
        return result
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        result.elapsed_ms = (time.perf_counter() - start) * 1000.0
        result.exception_category = _categorize_http_exc(exc)
        result.detail = str(exc)[:300]
        return result


def compare_http_probes(direct: HttpProbeResult, proxy_aware: HttpProbeResult) -> dict[str, Any]:
    """Summarize whether direct and proxy-aware paths differ."""

    differ = (
        direct.success != proxy_aware.success
        or direct.status_code != proxy_aware.status_code
        or direct.exception_category != proxy_aware.exception_category
    )
    return {
        "differ": differ,
        "direct_success": direct.success,
        "proxy_aware_success": proxy_aware.success,
        "interpretation": (
            "Direct and proxy-aware results differ — proxy path may interfere."
            if differ and direct.success and not proxy_aware.success
            else "Paths agree or both failed — proxy interference not uniquely supported."
            if not differ or (not direct.success and not proxy_aware.success)
            else "Results differ; review both probes before concluding proxy interference."
        ),
    }
