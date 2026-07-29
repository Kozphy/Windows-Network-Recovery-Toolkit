"""Initial versioned control catalog for endpoint reliability evidence."""

from __future__ import annotations

from .models import ControlDefinition, EvidenceRequirement


ENDPOINT_CONTROL_CATALOG: tuple[ControlDefinition, ...] = (
    ControlDefinition(
        control_id="CTRL-001",
        version="1.0",
        name="Dead WinINET Proxy Detection",
        objective="Confirm that WinINET proxy configuration is paired with runtime listener evidence.",
        requirements=(
            EvidenceRequirement(
                evidence_type="proxy_state",
                required_fields=("wininet_proxy_enabled", "wininet_proxy_server"),
                minimum_tier=1,
                description="WinINET proxy configuration captured",
            ),
            EvidenceRequirement(
                evidence_type="listener_state",
                required_fields=("listener_found", "localhost_port"),
                minimum_tier=2,
                description="Local listener state captured",
            ),
        ),
        owner="Endpoint Reliability",
    ),
    ControlDefinition(
        control_id="CTRL-002",
        version="1.0",
        name="WinINET / WinHTTP Stack Alignment",
        objective="Detect whether user and service proxy stacks have been compared.",
        requirements=(
            EvidenceRequirement(
                evidence_type="proxy_state",
                required_fields=("wininet_proxy_enabled", "winhttp_direct_access", "wininet_winhttp_mismatch"),
                minimum_tier=1,
                description="WinINET and WinHTTP state compared",
            ),
        ),
        owner="Platform Governance",
    ),
    ControlDefinition(
        control_id="CTRL-003",
        version="1.0",
        name="Direct vs Proxy Path Comparison",
        objective="Require independent direct and proxy path observations before path-level conclusions.",
        requirements=(
            EvidenceRequirement(
                evidence_type="probe_result",
                required_fields=("direct_probe_ok", "proxy_probe_ok"),
                minimum_tier=3,
                description="Direct and proxy path probes captured",
            ),
        ),
        owner="Endpoint Reliability",
    ),
)


def get_control(control_id: str) -> ControlDefinition | None:
    """Return a control by stable identifier."""

    normalized = (control_id or "").upper()
    return next((control for control in ENDPOINT_CONTROL_CATALOG if control.control_id == normalized), None)
