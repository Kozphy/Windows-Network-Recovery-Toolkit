"""Orchestrate ChatGPT connectivity auto-fix: proxy, diagnose, LOW-risk remediations."""

from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from windows_network_toolkit.diagnostics.bad_gateway import run_bad_gateway_diagnose
from windows_network_toolkit.diagnostics.proxy import run_proxy_status
from windows_network_toolkit.proxy_guardian import run_proxy_guardian_once

from .audit import append_network_recovery_audit
from .collectors import collect_signals
from .engine import run_scenario_diagnosis
from .models import SCENARIO_CHATGPT_APP_FIREWALL
from .remediation_executor import (
    CONFIRMATION_PHRASE,
    execute_selected_low_risk_actions,
    select_low_risk_actions,
)


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def run_auto_fix_chatgpt(
    *,
    dry_run: bool = False,
    confirm: str = "",
    skip_proxy_auto_fix: bool = False,
    skip_guardian_install: bool = False,
    chatgpt_url: str = "https://chatgpt.com",
    repo_root: Path | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Chain proxy guardian, bad-gateway diagnose, scenario diagnosis, and LOW-risk apply."""
    if platform.system() != "Windows":
        return {
            "unsupported_platform": True,
            "platform": platform.system(),
            "message": "auto-fix-chatgpt requires Windows.",
        }

    from windows_network_toolkit.safety import is_demo_mode

    if is_demo_mode():
        dry_run = True

    repo = _repo_root(repo_root)
    run_fn = run or subprocess.run
    effective_confirm = confirm if confirm else (CONFIRMATION_PHRASE if not dry_run else "")
    steps: list[dict[str, Any]] = []

    if not skip_proxy_auto_fix:
        guardian = run_proxy_guardian_once(dry_run=dry_run)
        steps.append({"step": "proxy_guardian", "result": guardian})
        proxy_status = run_proxy_status()
        steps.append({"step": "proxy_status", "result": proxy_status})
    else:
        proxy_status = run_proxy_status()
        steps.append({"step": "proxy_status", "result": proxy_status, "note": "proxy auto-fix skipped"})

    bad_gateway = run_bad_gateway_diagnose(chatgpt_url, dry_run=True)
    steps.append({"step": "bad_gateway_diagnose", "url": chatgpt_url, "result": bad_gateway})

    diagnosis = run_scenario_diagnosis(
        SCENARIO_CHATGPT_APP_FIREWALL,
        dry_run=dry_run,
        collect_live=True,
        run=run_fn,
    )
    last_path = repo / "reports" / "last_network_recovery_diagnosis.json"
    last_path.parent.mkdir(parents=True, exist_ok=True)
    last_path.write_text(json.dumps(diagnosis.to_audit_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    steps.append(
        {
            "step": "chatgpt_scenario_diagnose",
            "run_id": diagnosis.run_id,
            "primary_hypothesis": diagnosis.hypotheses[0].hypothesis_id if diagnosis.hypotheses else None,
            "signals": diagnosis.signals.to_dict(),
            "report_path": str(last_path),
        }
    )

    selected = select_low_risk_actions(diagnosis.signals, diagnosis.hypotheses)
    remediation = execute_selected_low_risk_actions(
        selected,
        dry_run=dry_run,
        confirm=effective_confirm,
        previews=diagnosis.recommended_actions,
        run=run_fn,
    )
    diagnosis.remediation_executed = list(remediation.get("executed", []))
    steps.append({"step": "low_risk_remediation", "result": remediation})

    if not dry_run and diagnosis.remediation_executed:
        post_signals = collect_signals(run=run_fn)
        diagnosis.post_check_results = {
            "chatgpt_https_ok": post_signals.chatgpt_https_ok,
            "openai_https_ok": post_signals.openai_https_ok,
            "browser_https_ok": post_signals.browser_https_ok,
            "dns_ok": post_signals.dns_ok,
        }
        steps.append({"step": "post_check", "result": diagnosis.post_check_results})

    append_network_recovery_audit(repo, diagnosis)

    classification = str(proxy_status.get("classification") or "")
    chatgpt_ok = diagnosis.signals.chatgpt_https_ok
    outcome = "healthy"
    if chatgpt_ok is False or classification == "DEAD_PROXY_CONFIG":
        outcome = "degraded"
    elif chatgpt_ok is None:
        outcome = "inconclusive"

    return {
        "dry_run": dry_run,
        "skip_proxy_auto_fix": skip_proxy_auto_fix,
        "skip_guardian_install": skip_guardian_install,
        "confirmation_token": CONFIRMATION_PHRASE,
        "outcome": outcome,
        "proxy_classification": classification,
        "chatgpt_https_ok": chatgpt_ok,
        "steps": steps,
        "diagnosis_run_id": diagnosis.run_id,
        "limitations": diagnosis.limitations,
    }
