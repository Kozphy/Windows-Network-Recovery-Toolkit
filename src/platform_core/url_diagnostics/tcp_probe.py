"""TCP connectivity probe for URL diagnostics."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from .models import ProbeStatus, TcpObservation


def probe_tcp(
    url: str,
    *,
    timeout: float = 10.0,
    inject: dict[str, Any] | None = None,
) -> TcpObservation:
    if inject is not None:
        return TcpObservation.model_validate(inject)

    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        return TcpObservation(status=ProbeStatus.FAIL, remote_host=host, remote_port=port, error="missing_host")

    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return TcpObservation(status=ProbeStatus.OK, remote_host=host, remote_port=port)
    except OSError as exc:
        return TcpObservation(
            status=ProbeStatus.FAIL,
            remote_host=host,
            remote_port=port,
            error=str(exc)[:300],
        )
