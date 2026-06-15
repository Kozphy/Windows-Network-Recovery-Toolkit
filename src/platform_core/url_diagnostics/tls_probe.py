"""TLS handshake probe for URL diagnostics."""

from __future__ import annotations

import socket
import ssl
from typing import Any
from urllib.parse import urlparse

from .models import ProbeStatus, TlsObservation


def probe_tls(
    url: str,
    *,
    timeout: float = 10.0,
    inject: dict[str, Any] | None = None,
) -> TlsObservation:
    if inject is not None:
        return TlsObservation.model_validate(inject)

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return TlsObservation(
            status=ProbeStatus.SKIPPED,
            sni=parsed.hostname or "",
            error="not_https",
        )

    host = parsed.hostname or ""
    port = parsed.port or 443
    if not host:
        return TlsObservation(status=ProbeStatus.FAIL, sni=host, error="missing_host")

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                subj = ", ".join("=".join(x) for x in cert.get("subject", ()))
                iss = ", ".join("=".join(x) for x in cert.get("issuer", ()))
        return TlsObservation(status=ProbeStatus.OK, issuer=iss, subject=subj, sni=host)
    except OSError as exc:
        return TlsObservation(status=ProbeStatus.FAIL, sni=host, error=str(exc)[:300])
