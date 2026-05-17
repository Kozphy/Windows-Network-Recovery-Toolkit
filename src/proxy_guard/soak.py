"""Post-remediation soak: detect ProxyEnable re-enable without reset loops."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .registry import read_proxy_registry


@dataclass(frozen=True)
class SoakResult:
    """Outcome of monitoring HKCU proxy keys after remediation."""

    status: str  # STABLE | REMEDIATION_NOT_STICKY
    soak_minutes: float
    poll_seconds: float
    samples: int
    detail: str
    last_proxy_enable: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "soak_minutes": self.soak_minutes,
            "poll_seconds": self.poll_seconds,
            "samples": self.samples,
            "detail": self.detail,
            "last_proxy_enable": self.last_proxy_enable,
        }


def run_remediation_soak(
    *,
    soak_minutes: float,
    poll_seconds: float = 5.0,
    run: Callable[..., Any],
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> SoakResult:
    """Poll WinINET ``ProxyEnable``; report sticky only if no OFF->ON re-enable."""

    if soak_minutes <= 0:
        return SoakResult(
            status="STABLE",
            soak_minutes=0.0,
            poll_seconds=poll_seconds,
            samples=0,
            detail="soak_skipped",
            last_proxy_enable=None,
        )

    deadline = monotonic_fn() + soak_minutes * 60.0
    samples = 0
    last_en: int | None = None
    while monotonic_fn() < deadline:
        reg = read_proxy_registry(run=run)
        samples += 1
        en = reg.proxy_enable
        last_en = en
        if en == 1:
            return SoakResult(
                status="REMEDIATION_NOT_STICKY",
                soak_minutes=soak_minutes,
                poll_seconds=poll_seconds,
                samples=samples,
                detail=(
                    "ProxyEnable returned to 1 during soak. Suspected active reverter. "
                    "Do not keep resetting in a loop — identify writer (WMI / Procmon / Sysmon EID 13)."
                ),
                last_proxy_enable=en,
            )
        sleep_fn(poll_seconds)

    return SoakResult(
        status="STABLE",
        soak_minutes=soak_minutes,
        poll_seconds=poll_seconds,
        samples=samples,
        detail="no_proxy_reenable_during_soak",
        last_proxy_enable=last_en,
    )
