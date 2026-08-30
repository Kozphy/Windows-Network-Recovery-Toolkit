"""Preview-only remediation recommendations for localhost diagnose."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .classifier import ClassificationResult


@dataclass
class RemediationPreviewItem:
    action_id: str
    summary: str
    detail: str
    policy_decision: str  # PREVIEW | BLOCK
    justification: str
    requires_confirmation: bool = True
    mutates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "summary": self.summary,
            "detail": self.detail,
            "policy_decision": self.policy_decision,
            "justification": self.justification,
            "requires_confirmation": self.requires_confirmation,
            "mutates": list(self.mutates),
        }


def build_remediation_preview(
    classification: ClassificationResult,
    *,
    target_url: str,
    ipv4_only_listener: bool = False,
    ipv6_only_listener: bool = False,
    nearby_ports: list[int] | None = None,
    service_name: str | None = None,
) -> list[RemediationPreviewItem]:
    """Generate safe PREVIEW/BLOCK recommendations — never auto-execute."""

    items: list[RemediationPreviewItem] = []
    code = classification.code

    items.append(
        RemediationPreviewItem(
            action_id="reopen_application",
            summary="Reopen the application that created this localhost page",
            detail=f"After the app is listening again, refresh {target_url}.",
            policy_decision="PREVIEW",
            justification="No listener / connection refused most often means the hosting app is not running.",
            requires_confirmation=False,
            mutates=[],
        )
    )

    if ipv4_only_listener:
        items.append(
            RemediationPreviewItem(
                action_id="retry_ipv4",
                summary="Retry using 127.0.0.1",
                detail="Listener appears IPv4-only; browsers resolving to ::1 may refuse.",
                policy_decision="PREVIEW",
                justification="Address-family bind mismatch observed.",
                requires_confirmation=False,
                mutates=[],
            )
        )
    if ipv6_only_listener:
        items.append(
            RemediationPreviewItem(
                action_id="retry_ipv6",
                summary="Retry using http://[::1]:<port>/…",
                detail="Listener appears IPv6-only.",
                policy_decision="PREVIEW",
                justification="Address-family bind mismatch observed.",
                requires_confirmation=False,
                mutates=[],
            )
        )

    if code == "LOCALHOST_PORT_CHANGED_POSSIBLE" and nearby_ports:
        port = nearby_ports[0]
        items.append(
            RemediationPreviewItem(
                action_id="consider_new_port",
                summary=f"Consider whether the app moved to port {port}",
                detail=(
                    "Nearby listener evidence is weak. Confirm same process/executable before changing bookmarks."
                ),
                policy_decision="PREVIEW",
                justification="Bounded nearby-listener correlation only — not proof of port replacement.",
                requires_confirmation=False,
                mutates=[],
            )
        )

    if code == "LOCALHOST_PROXY_INTERFERENCE":
        items.append(
            RemediationPreviewItem(
                action_id="proxy_remediation_preview_only",
                summary="Preview existing proxy remediation (do not auto-disable)",
                detail=(
                    "Use `python -m windows_network_toolkit proxy-disable --dry-run true` only if "
                    "dead localhost proxy is separately corroborated. Do not disable proxy merely "
                    "because a localhost page failed."
                ),
                policy_decision="PREVIEW",
                justification="Policy gate keeps proxy mutation preview-only without typed confirmation.",
                requires_confirmation=True,
                mutates=["wininet_proxy"],
            )
        )

    if service_name:
        items.append(
            RemediationPreviewItem(
                action_id="restart_allowlisted_service_preview",
                summary=f"Preview restart of identified service '{service_name}'",
                detail="Execution requires existing ALLOW policy and typed confirmation — not performed here.",
                policy_decision="PREVIEW",
                justification="Service was deterministically identified; still preview-only by default.",
                requires_confirmation=True,
                mutates=["windows_service"],
            )
        )
    else:
        items.append(
            RemediationPreviewItem(
                action_id="block_generic_restart",
                summary="Do not restart arbitrary executables or services",
                detail="No deterministically identified Windows service for this listener.",
                policy_decision="BLOCK",
                justification="Safety policy forbids fabricating restart commands for unknown processes.",
                requires_confirmation=True,
                mutates=[],
            )
        )

    # Always block firewall / proxy auto-mutation
    items.append(
        RemediationPreviewItem(
            action_id="block_firewall_change",
            summary="Do not modify firewall rules automatically",
            detail="CONNECTION_REFUSED is not firewall proof.",
            policy_decision="BLOCK",
            justification="Toolkit safety policy blocks firewall changes from diagnose.",
            mutates=["firewall"],
        )
    )
    items.append(
        RemediationPreviewItem(
            action_id="block_auto_proxy_disable",
            summary="Do not automatically disable the system proxy",
            detail="Proxy disable remains a separate gated command.",
            policy_decision="BLOCK",
            justification="Localhost listener failure is usually unrelated to system proxy state.",
            mutates=["wininet_proxy"],
        )
    )
    return items


def policy_envelope(*, remediation_requested: bool) -> dict[str, Any]:
    """Default policy decision for localhost diagnose."""

    return {
        "decision": "PREVIEW",
        "execution_authority": "preview_only",
        "dry_run": True,
        "remediation_requested": remediation_requested,
        "justification": (
            "localhost-diagnose is read-only; remediation items are previews unless an existing "
            "gated command is separately confirmed."
        ),
        "blocked_automatic_actions": [
            "firewall_modify",
            "proxy_disable",
            "registry_write",
            "service_restart",
            "process_kill",
        ],
    }
