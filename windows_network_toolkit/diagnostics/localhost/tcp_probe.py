"""TCP connectivity probes with normalized Windows/socket error categories."""

from __future__ import annotations

import errno
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

ErrorCategory = str  # CONNECTED | CONNECTION_REFUSED | TIMEOUT | ...


@dataclass(frozen=True)
class TcpProbeResult:
    address: str
    address_family: str
    port: int
    connect_success: bool
    elapsed_ms: float
    error_category: ErrorCategory
    windows_error_code: int | None
    detail: str
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "address_family": self.address_family,
            "port": self.port,
            "connect_success": self.connect_success,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "error_category": self.error_category,
            "windows_error_code": self.windows_error_code,
            "detail": self.detail,
            "timestamp_utc": self.timestamp_utc,
        }


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def categorize_socket_error(exc: BaseException) -> tuple[ErrorCategory, int | None, str]:
    """Map OSError/socket errors to normalized categories without overclaiming firewall."""

    if isinstance(exc, TimeoutError):
        return "TIMEOUT", getattr(exc, "winerror", None) or getattr(exc, "errno", None), str(exc)
    if isinstance(exc, socket.gaierror):
        return "NAME_RESOLUTION_FAILED", getattr(exc, "errno", None), str(exc)
    if isinstance(exc, PermissionError):
        return "PERMISSION_ERROR", getattr(exc, "winerror", None) or getattr(exc, "errno", None), str(exc)
    if isinstance(exc, OSError):
        win = getattr(exc, "winerror", None)
        en = getattr(exc, "errno", None)
        code = win if win is not None else en
        # WSAECONNREFUSED = 10061; ECONNREFUSED
        if code in {10061, errno.ECONNREFUSED} or en == errno.ECONNREFUSED:
            return (
                "CONNECTION_REFUSED",
                code if isinstance(code, int) else None,
                (
                    "Connection refused - typically no listener accepted the connection; "
                    "not by itself proof of a firewall block."
                ),
            )
        if code in {10060, errno.ETIMEDOUT} or en == errno.ETIMEDOUT:
            return "TIMEOUT", code if isinstance(code, int) else None, str(exc)
        if code in {10051, 10065, errno.ENETUNREACH, errno.EHOSTUNREACH}:
            return "NETWORK_UNREACHABLE", code if isinstance(code, int) else None, str(exc)
        if code in {10013, errno.EACCES}:
            return "PERMISSION_ERROR", code if isinstance(code, int) else None, str(exc)
        return "UNKNOWN_SOCKET_ERROR", code if isinstance(code, int) else None, str(exc)
    return "UNKNOWN_SOCKET_ERROR", None, str(exc)


def tcp_probe_address(
    address: str,
    port: int,
    *,
    timeout: float = 2.0,
) -> TcpProbeResult:
    """Probe one address:port with a bounded timeout (stdlib socket only)."""

    family = "IPv6" if ":" in address else "IPv4"
    start = time.perf_counter()
    try:
        with socket.create_connection((address, port), timeout=timeout):
            elapsed = (time.perf_counter() - start) * 1000.0
            return TcpProbeResult(
                address=address,
                address_family=family,
                port=port,
                connect_success=True,
                elapsed_ms=elapsed,
                error_category="CONNECTED",
                windows_error_code=None,
                detail=f"TCP connect to {address}:{port} succeeded",
                timestamp_utc=_now(),
            )
    except (OSError, TimeoutError) as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        category, code, detail = categorize_socket_error(exc)
        return TcpProbeResult(
            address=address,
            address_family=family,
            port=port,
            connect_success=False,
            elapsed_ms=elapsed,
            error_category=category,
            windows_error_code=code,
            detail=detail,
            timestamp_utc=_now(),
        )


def tcp_probe_many(
    addresses: list[str],
    port: int,
    *,
    timeout: float = 2.0,
) -> list[TcpProbeResult]:
    """Probe each address independently; preserves input order."""

    return [tcp_probe_address(addr, port, timeout=timeout) for addr in addresses]
