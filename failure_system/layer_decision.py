"""Layer-aware network failure decision engine with safe repair previews.

Module responsibility:
    Convert normalized probe signals into a single layer classification payload that preserves
    diagnosis-first safety boundaries and preview-only remediation guidance.

System placement:
    Sits after :mod:`failure_system.layer_probe` collection and before
    :mod:`failure_system.audit_log` persistence. Invoked directly via
    ``python -m failure_system.layer_decision`` and by batch wrappers under ``scripts/``.

Key invariants:
    - Returns a stable JSON shape for stdout, JSONL audit lines, and markdown report rendering.
    - Never executes state-changing repair commands; emits textual preview guidance only.
    - Attribution notes remain explicitly non-forensic unless upstream proof telemetry exists.

Audit Notes:
    Decision outputs are append-only and replayable via ``logs/network_layer_audit.jsonl``.
    If operators disagree with a decision, inspect ``observed_signals``/``hypotheses`` and rerun
    with additional evidence rather than executing blind repair actions.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from failure_system.audit_log import append_layer_audit, write_markdown_report
from failure_system.layer_probe import collect_layer_signals


def _now_iso() -> str:
    """Return timezone-aware UTC timestamp string for diagnosis payloads."""
    return datetime.now(timezone.utc).isoformat()


def _base_result() -> dict[str, Any]:
    """Create default decision payload with conservative unknown classification.

    Returns:
        dict[str, Any]: JSON-serializable baseline schema used by :func:`decide_layer`.

    Output guarantees:
        Includes all contract keys even when no strong signature is detected.
    """
    return {
        "timestamp": _now_iso(),
        "layer": "UNKNOWN",
        "failure_type": "no_strong_signature",
        "observed_signals": [],
        "hypotheses": [],
        "confidence_score": 0.2,
        "evidence_level": "observation",
        "recommended_next_test": "Re-run diagnosis and collect additional endpoint evidence.",
        "repair_preview": [],
        "safety_policy": {
            "diagnose_first": True,
            "requires_user_confirmation": True,
            "no_silent_process_kill": True,
            "no_silent_firewall_reset": True,
            "no_silent_adapter_disable": True,
            "no_registry_change_without_confirmation": True,
        },
        "attribution_notes": [],
    }


def _repair_preview(layer: str, signals: dict[str, Any]) -> list[str]:
    """Return safe preview-only operator guidance for a classified layer.

    Args:
        layer: Selected diagnosis layer label.
        signals: Normalized probe signal map.

    Returns:
        list[str]: Ordered textual preview actions; never executable commands.

    Constraints:
        Guidance intentionally avoids destructive or silent state mutation paths.
    """
    if layer == "L1_L2":
        return [
            "Preview only: Verify adapter enabled state and cable/Wi-Fi link.",
            "Preview only: Renew DHCP lease if gateway missing.",
        ]
    if layer == "L3":
        return [
            "Preview only: Verify route table and default gateway health.",
            "Preview only: Restart router/modem only after confirming multi-device symptoms.",
        ]
    if layer == "L4":
        return [
            "Preview only: Validate TCP 443 policy path (local firewall/endpoint controls).",
            "Preview only: Compare behavior on alternate network path (hotspot/VPN off).",
        ]
    if layer == "L7":
        out = [
            "Preview only: Compare WinINET and WinHTTP proxy states before any changes.",
            "Preview only: Restore previous proxy fields (ProxyEnable/ProxyServer/AutoConfigURL/ProxyOverride) with confirmation.",
        ]
        if signals.get("is_localhost_proxy"):
            out.append("Preview only: Confirm localhost proxy listener owner and health before disabling proxy.")
        return out
    if layer == "INFRA":
        return [
            "Preview only: Confirm router/ISP outage with second device before local stack changes.",
        ]
    return ["Preview only: gather more evidence before any repair action."]


def decide_layer(signals: dict[str, Any]) -> dict[str, Any]:
    """Classify failure layer using deterministic evidence-weighted rules.

    Args:
        signals: Normalized signal dictionary from :func:`failure_system.layer_probe.collect_layer_signals`.

    Returns:
        dict[str, Any]: Final decision payload containing layer, failure type, confidence,
        evidence level, hypotheses, recommended next test, and preview-only repair guidance.

    Decision intent:
        Rank likely failure layer first (L1/L2 → L3 → L4 → L7/INFRA) before any mutation path
        is considered, then expose confidence and rationale for operator review.

    Input assumptions:
        Missing keys are tolerated via ``dict.get`` and default to conservative classification.

    Failure modes:
        Conflicting signals (for example DNS + transport failures simultaneously) reduce confidence
        and shift evidence level toward ``observation``.

    Safe recovery guidance:
        Use ``recommended_next_test`` and rerun diagnosis to increase confidence before repairs.
    """
    result = _base_result()
    obs = result["observed_signals"]
    hyp = result["hypotheses"]
    notes = result["attribution_notes"]

    if signals.get("media_disconnected") or signals.get("adapter_down") or not signals.get("gateway_present"):
        result["layer"] = "L1_L2"
        result["failure_type"] = "link_or_adapter_failure"
        result["confidence_score"] = 0.9
        result["evidence_level"] = "inference"
        obs.extend(
            [
                f"media_disconnected={signals.get('media_disconnected')}",
                f"adapter_down={signals.get('adapter_down')}",
                f"gateway_present={signals.get('gateway_present')}",
            ]
        )
        hyp.append("Local link/adapter path is unhealthy before upstream checks.")
    elif signals.get("multi_device_failure_reported"):
        result["layer"] = "INFRA"
        result["failure_type"] = "upstream_or_router_failure"
        result["confidence_score"] = 0.85
        result["evidence_level"] = "inference"
        obs.append("multiple_devices_affected=true")
        hyp.append("Shared infrastructure is likely degraded (router/ISP/upstream).")
    elif not signals.get("ping_ip_ok"):
        result["layer"] = "L3"
        result["failure_type"] = "routing_or_gateway_reachability_failure"
        result["confidence_score"] = 0.75
        result["evidence_level"] = "inference"
        obs.append("ping_8_8_8_8=fail")
        hyp.append("IP path/routing is failing before transport/application checks.")
    elif signals.get("ping_ip_ok") and not signals.get("tcp_443_ok"):
        result["layer"] = "L4"
        result["failure_type"] = "transport_reachability_failure"
        result["confidence_score"] = 0.78
        result["evidence_level"] = "inference"
        obs.extend(["ping_8_8_8_8=ok", "tcp_443=fail"])
        hyp.append("Transport path likely blocked (firewall/policy/route edge).")
    elif signals.get("ping_ip_ok") and not signals.get("nslookup_ok"):
        result["layer"] = "L7"
        result["failure_type"] = "dns_resolution_failure"
        result["confidence_score"] = 0.82
        result["evidence_level"] = "inference"
        obs.extend(["ping_8_8_8_8=ok", "nslookup_google=fail"])
        hyp.append("DNS-only failure while IP reachability remains healthy.")
    elif signals.get("tcp_443_ok") and (not signals.get("curl_google_ok") or not signals.get("curl_ms_ok")):
        result["layer"] = "L7"
        result["failure_type"] = "https_or_browser_path_failure"
        result["confidence_score"] = 0.8
        result["evidence_level"] = "inference"
        obs.extend(["tcp_443=ok", "curl_https=fail"])
        hyp.append("Application path regressed after transport succeeds.")
    elif signals.get("winhttp_direct") and int(signals.get("wininet_proxy_enable") or 0) == 1:
        result["layer"] = "L7"
        result["failure_type"] = "browser_layer_proxy_drift"
        result["confidence_score"] = 0.86
        result["evidence_level"] = "inference"
        obs.extend(["winhttp=direct", "wininet_proxy_enable=1"])
        hyp.append("WinINET proxy drift can break browser traffic while WinHTTP remains direct.")
    if signals.get("is_localhost_proxy"):
        obs.append(f"wininet_proxy_server={signals.get('wininet_proxy_server')}")
        hyp.append("Local proxy interception hypothesis (localhost proxy endpoint configured).")
        notes.append("Localhost proxy attribution is heuristic unless direct registry-write telemetry exists.")
        if signals.get("localhost_listener_found") is True:
            obs.append("localhost_listener_found=true")
            result["confidence_score"] = min(1.0, float(result["confidence_score"]) + 0.05)
        elif signals.get("localhost_listener_found") is False:
            obs.append("localhost_listener_found=false")
            result["confidence_score"] = max(0.0, float(result["confidence_score"]) - 0.1)
            if result["layer"] == "UNKNOWN":
                result["layer"] = "L7"
                result["failure_type"] = "proxy_endpoint_unreachable"
                result["evidence_level"] = "inference"
    # Conflict handling intentionally reduces confidence and avoids strong causal claims.
    if signals.get("ping_ip_ok") and not signals.get("tcp_443_ok") and not signals.get("nslookup_ok"):
        result["confidence_score"] = max(0.3, float(result["confidence_score"]) - 0.2)
        result["failure_type"] = "conflicting_signals"
        result["evidence_level"] = "observation"
        hyp.append("Conflicting transport/DNS signals reduce confidence; additional tests required.")
    if signals.get("intermittent_snapshot"):
        result["confidence_score"] = max(0.25, float(result["confidence_score"]) - 0.15)
        hyp.append("Intermittent snapshot flag lowers confidence for single-pass diagnosis.")

    result["recommended_next_test"] = str(signals.get("recommended_next_test_hint") or result["recommended_next_test"])
    result["repair_preview"] = _repair_preview(str(result["layer"]), signals)
    return result


def run_layer_diagnosis(*, write_files: bool = True) -> dict[str, Any]:
    """Collect signals, classify layer, and optionally persist audit artifacts.

    Args:
        write_files: When True, append JSONL audit and markdown report outputs.

    Returns:
        dict[str, Any]: Final diagnosis payload emitted to callers/stdout.

    Side effects:
        Writes to ``logs/network_layer_audit.jsonl`` and ``reports/network_layer_diagnosis_*.md``
        when ``write_files`` is enabled.

    Idempotency:
        Re-running appends new timestamped rows/reports; no in-place mutation of prior artifacts.
    """
    signals = collect_layer_signals()
    result = decide_layer(signals)
    if write_files:
        append_layer_audit(result)
        write_markdown_report(result)
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for layer diagnosis workflow.

    Args:
        argv: Optional argument vector; defaults to process argv when ``None``.

    Returns:
        int: Exit code ``0`` on successful diagnosis emission.

    Side effects:
        Writes audit/report artifacts unless ``--no-write`` is provided.
    """
    parser = argparse.ArgumentParser(prog="failure_system.layer_decision")
    parser.add_argument("--no-write", action="store_true", help="Do not append audit/report files.")
    args = parser.parse_args(argv)
    payload = run_layer_diagnosis(write_files=not args.no_write)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

