"""Playwright browser evidence collector (optional dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from windows_network_toolkit.browser_evidence import BrowserEvidencePackage, summarize_har


def collect_browser_evidence(
    url: str,
    out_dir: Path,
    *,
    headless: bool = True,
    timeout_ms: int = 30_000,
) -> BrowserEvidencePackage:
    """Capture screenshot + HAR via Playwright. Requires `playwright` extra installed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshot = out_dir / "screenshot.png"
    har_path = out_dir / "network.har"
    trace_path = out_dir / "trace.zip"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright not installed — pip install '.[browser]' && playwright install chromium"
        ) from exc

    navigation_error: str | None = None
    tls_errors: list[str] = []
    proxy_hints: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(record_har_path=str(har_path))
        page = context.new_page()
        try:
            response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            if response and response.status >= 400:
                proxy_hints.append(f"http_status_{response.status}")
        except Exception as exc:
            navigation_error = str(exc)[:500]
            if "ERR_PROXY" in navigation_error.upper() or "PROXY" in navigation_error.upper():
                proxy_hints.append("proxy_connection_failure_suspected")
            if "SSL" in navigation_error.upper() or "CERT" in navigation_error.upper():
                tls_errors.append("tls_or_cert_error_during_navigation")
        try:
            page.screenshot(path=str(screenshot), full_page=True)
        except Exception:
            screenshot = Path("")
        context.close()
        browser.close()

    har_summary = summarize_har(har_path)
    if har_summary.get("failed", 0) > 0:
        proxy_hints.append("har_http_failures_present")

    return BrowserEvidencePackage(
        url=url,
        screenshot_path=str(screenshot) if screenshot else "",
        har_path=str(har_path),
        trace_path=str(trace_path) if trace_path.is_file() else "",
        navigation_error=navigation_error,
        tls_errors=tls_errors,
        proxy_hints=proxy_hints,
    )


def build_fixture_package(url: str = "https://example.com") -> dict[str, Any]:
    """Synthetic package for CI without live browser."""
    pkg = BrowserEvidencePackage(
        url=url,
        screenshot_path="tests/fixtures/browser_evidence/screenshot.png",
        har_path="tests/fixtures/browser_evidence/sample.har.json",
        navigation_error="ERR_PROXY_CONNECTION_FAILED",
        proxy_hints=["proxy_connection_failure_suspected"],
    )
    return pkg.model_dump()
