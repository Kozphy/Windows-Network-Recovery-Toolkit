"""Higher-order policy for HKCU proxy value transitions (PAC, localhost, trust paths).

Complements substring allowlists in :mod:`policy` — **default deny** for suspicious edits.
"""

from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any

from .models import AttributionResult, ProxyGuardPolicyDecision, ProxySnapshot
from .parser import ParsedProxy
from .planning import listen_port_for_attribution
from .pipeline import disabling_transition_allowed
from .policy import ProxyGuardPolicy, PolicyDecision


def hkcu_proxy_core_tuple(snapshot: ProxySnapshot) -> tuple[Any, ...]:
    """Comparable tuple for user-visible WinINET fields only."""
    return (
        snapshot.proxy_enable,
        snapshot.proxy_server,
        snapshot.proxy_override,
        snapshot.auto_config_url,
        snapshot.auto_detect,
    )


def _norm_str(val: str | None) -> str:
    return (val or "").strip()


def _exe_basename_candidate(process_exe: str | None, process_name: str | None) -> str | None:
    if process_exe:
        try:
            return PureWindowsPath(process_exe.strip().strip('"')).name.lower()
        except ValueError:
            pass
    if process_name:
        return str(process_name).lower()
    return None


def exe_path_trusted(candidate_path: str | None, prefixes: tuple[str, ...]) -> bool:
    """Return True when ``candidate_path`` sits under administrator-configured prefixes."""
    if not candidate_path or not prefixes:
        return False
    norm = candidate_path.strip().strip('"').lower().replace("/", "\\")
    for pref in prefixes:
        root = pref.strip().strip('"').lower().replace("/", "\\").rstrip("\\")
        if not root:
            continue
        if norm.startswith(root):
            return True
    return False


def attribution_to_owner_rows(attribution: AttributionResult) -> list[dict[str, Any]]:
    """Map :class:`~src.proxy_guard.models.AttributionResult` into legacy whitelist rows."""
    if attribution.process is None:
        return []
    proc = attribution.process
    basename = _exe_basename_candidate(proc.exe, proc.name)
    if not basename:
        return []
    return [{"process_name": basename, "pid": proc.pid}]


def evaluate_proxy_transition(
    *,
    prior_snap: ProxySnapshot,
    curr_snap: ProxySnapshot,
    parsed_prior: ParsedProxy,
    parsed_after: ParsedProxy,
    attribution: AttributionResult,
    policy: ProxyGuardPolicy,
    port_listen: bool | None,
) -> ProxyGuardPolicyDecision:
    """Classify registry transition with guarded defaults."""
    core_before = hkcu_proxy_core_tuple(prior_snap)
    core_after = hkcu_proxy_core_tuple(curr_snap)
    if core_before == core_after:
        return ProxyGuardPolicyDecision(
            decision="observe",
            reason="no_op_registry_core",
            matched_rule=None,
            rollback_allowed=False,
            rollback_required=False,
        )

    if disabling_transition_allowed(prior_snap, curr_snap):
        return ProxyGuardPolicyDecision(
            decision="allowed",
            reason="proxy_disable_transition_allowed_default",
            matched_rule=None,
            rollback_allowed=False,
            rollback_required=False,
        )

    pac_prev = _norm_str(prior_snap.auto_config_url)
    pac_curr = _norm_str(curr_snap.auto_config_url)
    if pac_prev != pac_curr and pac_curr:
        subs = getattr(policy, "allowed_autoconfig_url_substrings", ())
        matched_rule: str | None = None
        for s in subs:
            if str(s).lower() in pac_curr.lower():
                matched_rule = f"allow_autoconfig_substring:{s}"
                break
        if matched_rule is None:
            return ProxyGuardPolicyDecision(
                decision="blocked",
                reason="autoconfig_url_change_not_allowlisted",
                matched_rule=None,
                rollback_allowed=True,
                rollback_required=False,
            )

    if attribution.mode == "verified_eventlog" and attribution.process is not None:
        if exe_path_trusted(attribution.process.exe, getattr(policy, "trusted_exe_paths", ())):
            return ProxyGuardPolicyDecision(
                decision="allowed",
                reason="trusted_exe_path_verified_eventlog",
                matched_rule="trusted_exe_paths",
                rollback_allowed=False,
                rollback_required=False,
            )

    if parsed_after.is_localhost_proxy:
        port_guess = listen_port_for_attribution(parsed_after)
        base_rows = attribution_to_owner_rows(attribution)
        pd_name: PolicyDecision = policy.evaluate(base_rows)
        trusted_path = attribution.process is not None and exe_path_trusted(
            attribution.process.exe,
            getattr(policy, "trusted_exe_paths", ()),
        )
        verified_event = attribution.mode == "verified_eventlog"
        listener_ok = port_listen is True
        if listener_ok or trusted_path or verified_event or pd_name.allowed:
            rule = pd_name.matched_rule or ("localhost_listener_present" if listener_ok else "trusted_override")
            return ProxyGuardPolicyDecision(
                decision="allowed",
                reason="localhost_loopback_policy_allow",
                matched_rule=str(rule),
                rollback_allowed=False,
                rollback_required=False,
            )
        if port_listen is False:
            return ProxyGuardPolicyDecision(
                decision="blocked",
                reason="loopback_proxy_without_listener_and_untrusted",
                matched_rule=None,
                rollback_allowed=True,
                rollback_required=False,
            )

    pd = policy.evaluate(attribution_to_owner_rows(attribution))
    if pd.allowed:
        return ProxyGuardPolicyDecision(
            decision="allowed",
            reason=pd.reason,
            matched_rule=pd.matched_rule,
            rollback_allowed=False,
            rollback_required=False,
        )

    if policy.observe_only_when_unknown_attribution and (
        attribution.mode == "unknown" or attribution.process is None
    ):
        return ProxyGuardPolicyDecision(
            decision="observe",
            reason="observe_only_unknown_attribution_user_manual_mode",
            matched_rule=None,
            rollback_allowed=False,
            rollback_required=False,
        )

    return ProxyGuardPolicyDecision(
        decision="blocked",
        reason=pd.reason,
        matched_rule=None,
        rollback_allowed=True,
        rollback_required=False,
    )
