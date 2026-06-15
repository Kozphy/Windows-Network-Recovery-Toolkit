"""DNS resolution probe for URL diagnostics."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from .models import DnsObservation, ProbeStatus


def probe_dns(
    url: str,
    *,
    timeout: float = 10.0,
    inject: dict[str, Any] | None = None,
) -> DnsObservation:
    if inject is not None:
        return DnsObservation.model_validate(inject)

    host = urlparse(url).hostname or ""
    if not host:
        return DnsObservation(status=ProbeStatus.FAIL, error="missing_hostname")

    try:
        socket.setdefaulttimeout(timeout)
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        ips = sorted({item[4][0] for item in infos})
        if not ips:
            return DnsObservation(status=ProbeStatus.FAIL, error="no_addresses")
        return DnsObservation(status=ProbeStatus.OK, resolved_ips=ips)
    except OSError as exc:
        return DnsObservation(status=ProbeStatus.FAIL, error=str(exc)[:300])
