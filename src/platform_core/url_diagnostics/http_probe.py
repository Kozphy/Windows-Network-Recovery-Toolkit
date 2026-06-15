"""HTTP fetch probe with redirect capture."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import httpx

from .models import HttpObservation, ProbeStatus, RedirectHop

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()[:500]


def _body_fingerprint(body: bytes) -> str:
    return hashlib.sha256(body[:8192]).hexdigest()[:16]


def probe_http(
    url: str,
    *,
    follow_redirects: bool = True,
    max_redirects: int = 10,
    user_agent: str = "",
    timeout: float = 10.0,
    no_body: bool = False,
    inject: dict[str, Any] | None = None,
) -> HttpObservation:
    if inject is not None:
        return HttpObservation.model_validate(inject)

    headers = {"User-Agent": user_agent or _DEFAULT_UA}
    try:
        with httpx.Client(
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            timeout=timeout,
            headers=headers,
        ) as client:
            if no_body:
                resp = client.head(url)
                body = b""
            else:
                resp = client.get(url)
                body = resp.content

        chain: list[str] = [url]
        hops: list[RedirectHop] = []
        for hop in resp.history:
            chain.append(str(hop.url))
            hops.append(RedirectHop(url=str(hop.url), status_code=hop.status_code))
        final = str(resp.url)
        if final not in chain:
            chain.append(final)

        html = body.decode("utf-8", errors="replace") if body else ""
        proxy_error = False

        return HttpObservation(
            status=ProbeStatus.OK,
            status_code=resp.status_code,
            final_url=final,
            redirect_chain=chain,
            redirect_hops=hops,
            content_type=resp.headers.get("content-type", ""),
            title=_extract_title(html),
            body_fingerprint=_body_fingerprint(body) if body else "",
            body_length=len(body),
            proxy_error=proxy_error,
        )
    except httpx.ProxyError as exc:
        return HttpObservation(
            status=ProbeStatus.FAIL,
            error=str(exc)[:300],
            proxy_error=True,
        )
    except httpx.TooManyRedirects as exc:
        return HttpObservation(
            status=ProbeStatus.FAIL,
            error=str(exc)[:300],
            redirect_chain=[url],
        )
    except httpx.HTTPError as exc:
        return HttpObservation(
            status=ProbeStatus.FAIL,
            error=str(exc)[:300],
        )


def probe_http_browser_ua(
    url: str,
    *,
    timeout: float = 10.0,
    inject: bool | None = None,
) -> bool | None:
    """Optional second fetch with a browser-like UA; inject for tests."""
    if inject is not None:
        return inject
    obs = probe_http(
        url,
        follow_redirects=True,
        timeout=timeout,
        user_agent=_DEFAULT_UA,
    )
    return obs.status == ProbeStatus.OK and obs.status_code is not None
