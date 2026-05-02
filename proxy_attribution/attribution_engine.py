"""Orchestrate proxy detection, port ownership, classification, and persistence hints."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from proxy_attribution.classifier import (
    classify_proxy_source,
    recommended_action_and_risk,
)
from proxy_attribution.port_mapper import map_local_proxy_port, parse_local_proxy_server
from proxy_attribution.proxy_detector import _run_argv, collect_proxy_snapshot


def _run_reg_query_run_key() -> str:
    code, out = _run_argv(
        ["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"],
        timeout=20.0,
    )
    return out if code == 0 else ""


def _process_auto_start_hints(process_name: str | None) -> bool:
    """Return ``True`` if ``process_name`` appears referenced in Run or Startup folder."""

    if not process_name:
        return False
    base = process_name.lower().strip()
    stem = Path(base).name.lower()

    run_blob = _run_reg_query_run_key().lower()
    if stem and stem in run_blob:
        return True

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return False
    startup = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    if not startup.is_dir():
        return False
    stem_simple = stem.replace(".exe", "")
    try:
        for child in startup.iterdir():
            name_l = child.name.lower()
            if stem_simple and stem_simple in name_l:
                return True
            if stem and stem in name_l:
                return True
    except OSError:
        return False
    return False


def _build_explanation(
    *,
    classification: str,
    owner_process: str | None,
    localhost_mapped: bool,
    classifier_note: str,
) -> str:
    """Plain-language summary for UI or Failure Knowledge payloads."""

    owner_bit = (
        f"Ownership points to {owner_process}."
        if owner_process
        else "No listening process was attributed on the localhost proxy port."
    )
    map_bit = (
        "Netstat shows an active listener on the proxy port."
        if localhost_mapped
        else "No matching LISTENING socket was found for the configured localhost port."
    )
    return f"{classifier_note} {owner_bit} {map_bit}".strip()


def run_attribution() -> dict[str, Any]:
    """Execute read-only attribution pipeline and return a JSON-serializable dict.

    Side effects:
        Subprocess-only reads (``reg``, ``netsh``, ``netstat``, ``tasklist``). No registry writes.

    Failure modes:
        Non-Windows hosts return structured placeholders with ``note`` fields where probes are skipped.
    """

    snap = collect_proxy_snapshot()
    proxy_signal_active = snap.proxy_enabled or snap.winhttp_summary == "PROXY_CONFIGURED"

    mapping = map_local_proxy_port(snap.proxy_server)
    localhost_mapped = bool(
        mapping
        and mapping.get("listening_state")
        and mapping.get("listening_state") != "NOT_FOUND"
        and mapping.get("pid")
    )

    owner_process = mapping.get("process_name") if mapping else None
    pid = mapping.get("pid") if mapping else None
    listen_state = mapping.get("listening_state") if mapping else None

    classification, confidence, cls_note = classify_proxy_source(
        process_name=owner_process,
        proxy_signal_active=proxy_signal_active,
        proxy_server=snap.proxy_server,
        localhost_port_mapped=localhost_mapped,
    )

    auto_start = _process_auto_start_hints(owner_process)
    if owner_process and auto_start:
        confidence = min(0.98, confidence + 0.05)

    rec_action, risk = recommended_action_and_risk(classification)
    explanation = _build_explanation(
        classification=classification,
        owner_process=owner_process,
        localhost_mapped=bool(localhost_mapped),
        classifier_note=cls_note,
    )

    _, port = parse_local_proxy_server(snap.proxy_server)
    out: dict[str, Any] = {
        "proxy_enabled": snap.proxy_enabled,
        "proxy_server": snap.proxy_server or "",
        "auto_config_url": snap.auto_config_url or "",
        "winhttp_proxy": snap.winhttp_summary,
        "winhttp_direct": snap.winhttp_direct,
        "owner_process": owner_process or "",
        "pid": pid if pid is not None else 0,
        "listening_state": listen_state or "",
        "proxy_port": port if port is not None else 0,
        "classification": classification,
        "auto_start": auto_start,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "recommended_action": rec_action,
        "risk_level": risk,
        "explanation": explanation,
    }

    return out


def run_attribution_json() -> str:
    """Return compact JSON string for CLI consumers."""

    return json.dumps(run_attribution(), indent=2)
