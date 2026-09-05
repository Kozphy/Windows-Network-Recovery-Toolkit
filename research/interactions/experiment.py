"""Factorial fixture builders and experiment execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from research.interactions.models import InteractionCase, InteractionObservation
from windows_network_toolkit.analytics_pipeline import normalize_events_from_fixture
from windows_network_toolkit.incident_classifier import classify_incident_from_events

_FAILURE_CLASSES = frozenset(
    {
        "DEAD_PROXY_CONFIG",
        "BOTH_DIRECT_AND_PROXY_FAIL",
        "DIRECT_ONLY_WORKS",
        "LISTENER_NOT_PROXY",
        "PROXY_FORWARDING_FAILED",
        "WININET_WINHTTP_MISMATCH",
        "POSSIBLE_MITM_RISK",
        "REVERTER_SUSPECTED",
        "PROXY_FLAPPING",
    }
)

_HIGH_RISK = frozenset({"HIGH", "CRITICAL"})


def _base_proxy_state(proxy_fault: int, *, port: int) -> dict[str, Any]:
    return {
        "wininet_proxy_enabled": bool(proxy_fault),
        "wininet_proxy_server": f"127.0.0.1:{port}" if proxy_fault else "",
        "winhttp_direct_access": not bool(proxy_fault),
        "localhost_port": port if proxy_fault else None,
    }


def _severity_table(cells: dict[tuple[int, int], float]) -> Callable[[int, int], float]:
    def _lookup(x1: int, x2: int) -> float:
        return cells[(x1, x2)]

    return _lookup


def build_proxy_x_firewall(
    x1: int, x2: int, *, replicate: int
) -> tuple[dict[str, Any], int, float]:
    """Proxy fault × firewall filtering interaction."""
    port = 59081 + replicate
    proxy_fault = x1
    firewall_fault = x2
    fixture: dict[str, Any] = {
        "proxy_state": _base_proxy_state(proxy_fault, port=port),
        "proxy_owner": {
            "listener_found": not bool(proxy_fault),
            "localhost_port": port if proxy_fault else None,
        },
        "health_inject": {
            "direct_probe_ok": firewall_fault == 0,
            "proxy_probe_ok": proxy_fault == 0,
            "proxy_status": (
                "DEAD_PROXY"
                if proxy_fault
                else ("FIREWALL_BLOCKED" if firewall_fault else "DIRECT_OK")
            ),
        },
        "research_meta": {
            "experiment_id": "proxy_x_firewall",
            "firewall_filtering": bool(firewall_fault),
        },
    }
    severity = _severity_table({(0, 0): 0.0, (1, 0): 0.45, (0, 1): 0.40, (1, 1): 0.85})(x1, x2)
    y_failure = 1 if severity >= 0.35 else 0
    return fixture, y_failure, severity


def build_proxy_x_tls(x1: int, x2: int, *, replicate: int) -> tuple[dict[str, Any], int, float]:
    """Proxy fault × TLS/path mismatch interaction."""
    port = 60505 + replicate
    proxy_fault = x1
    tls_fault = x2
    fixture: dict[str, Any] = {
        "proxy_state": _base_proxy_state(proxy_fault, port=port),
        "proxy_owner": {
            "listener_found": not bool(proxy_fault),
            "localhost_port": port if proxy_fault else None,
        },
        "health_inject": {
            "direct_probe_ok": tls_fault == 0,
            "proxy_probe_ok": proxy_fault == 0,
            "proxy_status": "DEAD_PROXY" if proxy_fault else "DIRECT_OK",
        },
        "path_health": {
            "timestamp_utc": "2026-08-15T00:00:00Z",
            "classification": "POSSIBLE_MITM_RISK" if tls_fault else "PATH_OK",
            "tls_cert_mismatch": bool(tls_fault),
        },
        "research_meta": {"experiment_id": "proxy_x_tls", "tls_path_fault": bool(tls_fault)},
    }
    severity = _severity_table({(0, 0): 0.0, (1, 0): 0.50, (0, 1): 0.35, (1, 1): 0.92})(x1, x2)
    y_failure = 1 if severity >= 0.30 else 0
    return fixture, y_failure, severity


def build_wininet_x_winhttp(
    x1: int, x2: int, *, replicate: int
) -> tuple[dict[str, Any], int, float]:
    """WinINET proxy enabled × WinHTTP direct-access mismatch."""
    port = 8080 + replicate
    wininet_on = x1
    winhttp_direct = x2
    fixture: dict[str, Any] = {
        "proxy_state": {
            "wininet_proxy_enabled": bool(wininet_on),
            "wininet_proxy_server": f"127.0.0.1:{port}" if wininet_on else "",
            "winhttp_direct_access": bool(winhttp_direct),
            "localhost_port": port if wininet_on else None,
        },
        "proxy_owner": {
            "listener_found": bool(wininet_on),
            "localhost_port": port if wininet_on else None,
            "process": {"name": "node.exe", "pid": 4000 + replicate},
        },
        "health_inject": {
            "direct_probe_ok": True,
            "proxy_probe_ok": wininet_on == 0 or winhttp_direct == 0,
            "proxy_status": (
                "HEALTHY_LOCALHOST_PROXY" if wininet_on and not winhttp_direct else "DIRECT_OK"
            ),
        },
        "research_meta": {
            "experiment_id": "wininet_x_winhttp",
            "stack_mismatch": bool(wininet_on and winhttp_direct),
        },
    }
    mismatch = bool(wininet_on and winhttp_direct)
    severity = _severity_table({(0, 0): 0.0, (1, 0): 0.20, (0, 1): 0.10, (1, 1): 0.75})(x1, x2)
    if mismatch:
        severity = max(severity, 0.75)
    y_failure = 1 if severity >= 0.25 else 0
    return fixture, y_failure, severity


def build_proxy_x_listener(
    x1: int, x2: int, *, replicate: int
) -> tuple[dict[str, Any], int, float]:
    """Proxy enabled × listener attribution present interaction."""
    port = 59999 + replicate
    proxy_on = x1
    listener_present = x2
    fixture: dict[str, Any] = {
        "proxy_state": _base_proxy_state(proxy_on, port=port),
        "proxy_owner": {
            "listener_found": bool(listener_present),
            "localhost_port": port if proxy_on else None,
            "process": (
                {"name": "unknown.exe", "pid": 5000 + replicate} if listener_present else None
            ),
        },
        "health_inject": {
            "direct_probe_ok": True,
            "proxy_probe_ok": bool(listener_present) if proxy_on else True,
            "proxy_status": (
                "HEALTHY_LOCALHOST_PROXY"
                if proxy_on and listener_present
                else ("DEAD_PROXY" if proxy_on else "DIRECT_OK")
            ),
        },
        "research_meta": {
            "experiment_id": "proxy_x_listener",
            "listener_present": bool(listener_present),
        },
    }
    severity = _severity_table({(0, 0): 0.0, (1, 0): 0.55, (0, 1): 0.05, (1, 1): 0.25})(x1, x2)
    y_failure = 1 if severity >= 0.30 else 0
    return fixture, y_failure, severity


def build_dns_x_proxy(x1: int, x2: int, *, replicate: int) -> tuple[dict[str, Any], int, float]:
    """DNS resolution fault × proxy fault interaction."""
    port = 3128 + replicate
    dns_fault = x1
    proxy_fault = x2
    fixture: dict[str, Any] = {
        "proxy_state": _base_proxy_state(proxy_fault, port=port),
        "proxy_owner": {
            "listener_found": not bool(proxy_fault),
            "localhost_port": port if proxy_fault else None,
        },
        "health_inject": {
            "direct_probe_ok": dns_fault == 0,
            "proxy_probe_ok": proxy_fault == 0,
            "proxy_status": (
                "DEAD_PROXY" if proxy_fault else ("DNS_FAILURE" if dns_fault else "DIRECT_OK")
            ),
        },
        "research_meta": {"experiment_id": "dns_x_proxy", "dns_fault": bool(dns_fault)},
    }
    severity = _severity_table({(0, 0): 0.0, (1, 0): 0.42, (0, 1): 0.48, (1, 1): 0.88})(x1, x2)
    y_failure = 1 if severity >= 0.35 else 0
    return fixture, y_failure, severity


def build_listener_x_process(
    x1: int, x2: int, *, replicate: int
) -> tuple[dict[str, Any], int, float]:
    """Listener present × process attribution trust interaction."""
    port = 7070 + replicate
    listener_present = x1
    trusted_process = x2
    process = (
        {"name": "node.exe", "pid": 6000 + replicate}
        if trusted_process
        else {"name": "unknown.exe", "pid": 7000 + replicate}
    )
    fixture: dict[str, Any] = {
        "proxy_state": _base_proxy_state(1, port=port),
        "proxy_owner": {
            "listener_found": bool(listener_present),
            "localhost_port": port,
            "process": process if listener_present else None,
        },
        "health_inject": {
            "direct_probe_ok": True,
            "proxy_probe_ok": bool(listener_present and trusted_process),
            "proxy_status": (
                "HEALTHY_LOCALHOST_PROXY"
                if listener_present and trusted_process
                else ("DEAD_PROXY" if not listener_present else "UNKNOWN_LOCAL_PROXY")
            ),
        },
        "research_meta": {
            "experiment_id": "listener_x_process",
            "listener_present": bool(listener_present),
            "trusted_process_attribution": bool(trusted_process),
        },
    }
    severity = _severity_table({(0, 0): 0.55, (0, 1): 0.55, (1, 0): 0.45, (1, 1): 0.15})(x1, x2)
    y_failure = 1 if severity >= 0.30 else 0
    return fixture, y_failure, severity


EXPERIMENT_BUILDERS: list[dict[str, Any]] = [
    {
        "experiment_id": "proxy_x_firewall",
        "factor_a_name": "proxy_fault",
        "factor_b_name": "firewall_fault",
        "description": "Dead/misconfigured localhost proxy × outbound firewall filtering.",
        "builder": build_proxy_x_firewall,
    },
    {
        "experiment_id": "proxy_x_tls",
        "factor_a_name": "proxy_fault",
        "factor_b_name": "tls_path_fault",
        "description": "Proxy misconfiguration × TLS/path certificate mismatch.",
        "builder": build_proxy_x_tls,
    },
    {
        "experiment_id": "wininet_x_winhttp",
        "factor_a_name": "wininet_proxy_enabled",
        "factor_b_name": "winhttp_direct_access",
        "description": "WinINET proxy state × WinHTTP direct-access stack mismatch.",
        "builder": build_wininet_x_winhttp,
    },
    {
        "experiment_id": "proxy_x_listener",
        "factor_a_name": "proxy_enabled",
        "factor_b_name": "listener_present",
        "description": "WinINET proxy enabled × localhost listener attribution present.",
        "builder": build_proxy_x_listener,
    },
    {
        "experiment_id": "dns_x_proxy",
        "factor_a_name": "dns_fault",
        "factor_b_name": "proxy_fault",
        "description": "DNS resolution failure × localhost proxy fault.",
        "builder": build_dns_x_proxy,
    },
    {
        "experiment_id": "listener_x_process",
        "factor_a_name": "listener_present",
        "factor_b_name": "trusted_process_attribution",
        "description": "Localhost listener present × trusted vs unknown process attribution.",
        "builder": build_listener_x_process,
    },
]


def generate_factorial_cases(
    spec: dict[str, Any],
    *,
    replicates: int = 3,
) -> list[InteractionCase]:
    """Generate full 2x2 factorial with replicates per cell."""
    builder = spec["builder"]
    cases: list[InteractionCase] = []
    exp_id = spec["experiment_id"]
    for x1 in (0, 1):
        for x2 in (0, 1):
            for rep in range(replicates):
                fixture, y_fail, y_sev = builder(x1, x2, replicate=rep)
                case_id = f"IX-{exp_id}-{x1}{x2}-r{rep}"
                cases.append(
                    InteractionCase(
                        experiment_id=exp_id,
                        case_id=case_id,
                        factor_a_name=spec["factor_a_name"],
                        factor_b_name=spec["factor_b_name"],
                        x1=x1,
                        x2=x2,
                        replicate=rep,
                        fixture=fixture,
                        y_failure=y_fail,
                        y_severity=y_sev,
                        limitations=[
                            "Synthetic factorial fixture — not live enterprise telemetry.",
                            "Designed severity supports interaction contrast; not calibrated probability.",
                        ],
                    )
                )
    return cases


def _platform_severity(
    incident_class: str, confidence: float, risk_level: str
) -> tuple[int, float]:
    if incident_class in _FAILURE_CLASSES or risk_level in _HIGH_RISK:
        sev = min(1.0, 0.55 + confidence * 0.45)
        return 1, sev
    if incident_class in {"INSUFFICIENT_DATA", "UNKNOWN"}:
        return 0, 0.25
    return 0, max(0.0, confidence * 0.3)


def evaluate_case(case: InteractionCase) -> InteractionObservation:
    """Run canonical classifier on factorial fixture (read-only)."""
    events = normalize_events_from_fixture(case.fixture)
    incident = classify_incident_from_events(events)
    y_pf, y_ps = _platform_severity(
        incident.incident_class,
        incident.confidence,
        incident.risk_level,
    )
    return InteractionObservation(
        **case.model_dump(),
        y_platform_failure=y_pf,
        y_platform_severity=y_ps,
        incident_class=incident.incident_class,
        classifier_confidence=incident.confidence,
    )


def cases_digest(cases: list[InteractionCase]) -> str:
    payload = [c.model_dump(mode="json") for c in cases]
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_interaction_experiments(
    *,
    replicates: int = 3,
    experiment_ids: list[str] | None = None,
) -> tuple[list[InteractionObservation], list[InteractionCase]]:
    """Generate and evaluate all interaction experiments."""
    specs = EXPERIMENT_BUILDERS
    if experiment_ids:
        allowed = set(experiment_ids)
        specs = [s for s in specs if s["experiment_id"] in allowed]

    all_cases: list[InteractionCase] = []
    observations: list[InteractionObservation] = []
    for spec in specs:
        cases = generate_factorial_cases(spec, replicates=replicates)
        all_cases.extend(cases)
        observations.extend(evaluate_case(c) for c in cases)
    return observations, all_cases


def run_timestamp() -> str:
    return datetime.now(tz=UTC).isoformat()
