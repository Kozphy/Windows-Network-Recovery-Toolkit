"""Certificate-store risk indicator collector (preview only).

Module responsibility:
    Inspect trusted-root stores and flag suspicious/recent certificate indicators that can
    increase interception risk hypotheses.

System placement:
    Supplemental collector for :mod:`proxy_guard.main` before pure inference scoring.

Safety boundary:
    Read-only certificate enumeration only; no trust-store modifications.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

_LOGGER = logging.getLogger(__name__)
_SUSPICIOUS_TOKENS = (
    "mitm",
    "intercept",
    "interception",
    "fiddler",
    "burp",
    "charles",
    "mitmproxy",
    "proxyman",
    "owasp",
    "zap",
    "packet",
)
_COMMON_TRUSTED_TOKENS = (
    "microsoft",
    "digicert",
    "globalsign",
    "let's encrypt",
    "isrg",
    "entrust",
    "sectigo",
    "comodoca",
    "verisign",
    "certum",
    "google trust services",
    "amazon",
    "starfield",
    "comodo",
    "usertrust",
    "thawte",
    "godaddy",
    "ssl.com",
    "secom",
    "twca",
    "taiwan-ca",
    "chunghwa",
    "government root",
    "china financial",
)


def _run(argv: list[str], timeout_seconds: float = 30.0) -> tuple[int, str]:
    """Execute one certificate-related probe command.

    Args:
        argv: Command arguments passed with ``shell=False``.
        timeout_seconds: Maximum runtime.

    Returns:
        Tuple of return code and merged stdout/stderr text.
    """
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _LOGGER.debug("Certificate command failed: %s", exc)
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _load_roots() -> list[dict[str, Any]]:
    """Enumerate CurrentUser/LocalMachine root certificate stores.

    Returns:
        list[dict[str, Any]]: Flat certificate records when command succeeds, else empty list.
    """
    ps = (
        "$roots=@(); "
        "$roots += Get-ChildItem Cert:\\CurrentUser\\Root | Select-Object Subject,Issuer,NotBefore,NotAfter,Thumbprint,@{N='Store';E={'CurrentUser'}}; "
        "$roots += Get-ChildItem Cert:\\LocalMachine\\Root | Select-Object Subject,Issuer,NotBefore,NotAfter,Thumbprint,@{N='Store';E={'LocalMachine'}}; "
        "$roots | ConvertTo-Json -Compress"
    )
    code, out = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout_seconds=40.0)
    if code != 0 or not out.strip():
        return []
    try:
        blob = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(blob, dict):
        return [blob]
    if isinstance(blob, list):
        return [x for x in blob if isinstance(x, dict)]
    return []


def _parse_powershell_datetime(value: Any) -> datetime | None:
    """Parse common PowerShell JSON DateTime encodings.

    Args:
        value: PowerShell JSON date value such as ISO text or ``/Date(1714600000000)/``.

    Returns:
        Timezone-aware UTC datetime when parsed, otherwise ``None``.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    dotnet_match = re.match(r"^/Date\((?P<millis>-?\d+)(?:[+-]\d+)?\)/$", text)
    if dotnet_match:
        millis = int(dotnet_match.group("millis"))
        return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text_blob(cert: dict[str, Any]) -> str:
    """Return searchable certificate subject/issuer text."""
    return f"{cert.get('Subject') or ''} {cert.get('Issuer') or ''}".lower()


def _has_common_trusted_name(cert: dict[str, Any]) -> bool:
    """Return whether certificate subject/issuer contains a common public CA token."""
    blob = _text_blob(cert)
    return any(token in blob for token in _COMMON_TRUSTED_TOKENS)


def _with_reason(cert: dict[str, Any], reason: str) -> dict[str, Any]:
    """Copy a certificate row with a suspicious indicator reason."""
    row = dict(cert)
    row["indicator_reason"] = reason
    return row


def collect_certificate_indicators() -> dict[str, Any]:
    """Collect root-store signals and suspicious certificate hints.

    Returns:
        dict[str, Any]: Suspicious certificate rows, recent root additions, unknown issuer
        candidates, and limitations.

    Constraints:
        "Recently added" uses ``NotBefore`` as an approximation; install time is not directly
        available from this collector.

    Audit Notes:
        Suspicious cert flags are heuristic indicators and should be validated with enterprise PKI
        policy before incident escalation.
    """
    if platform.system().lower() != "windows":
        return {
            "root_certificate_count": 0,
            "suspicious_certificates": [],
            "recent_root_additions": [],
            "unknown_issuer_candidates": [],
            "unknown_issuer_candidate_count": 0,
            "observations": ["Trusted root certificates were not inspected because platform is not Windows."],
            "limitations": ["non_windows_platform"],
        }
    now = datetime.now(timezone.utc)
    suspicious: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    unknown_issuers: list[dict[str, Any]] = []
    unknown_issuer_count = 0
    roots = _load_roots()
    for cert in roots:
        blob = _text_blob(cert)
        has_tool_token = any(token in blob for token in _SUSPICIOUS_TOKENS)
        if has_tool_token:
            suspicious.append(_with_reason(cert, "common_interception_tool_certificate_name"))
        # Heuristic "recently added" approximation from NotBefore when available.
        dt = _parse_powershell_datetime(cert.get("NotBefore"))
        if not _has_common_trusted_name(cert):
            unknown_issuer_count += 1
        if dt is None:
            continue
        is_recent = (now - dt).days <= 30
        if not _has_common_trusted_name(cert) and (is_recent or has_tool_token):
            unknown_issuers.append(_with_reason(cert, "recent_or_toollike_unknown_root_issuer"))
        if is_recent:
            recent.append(_with_reason(cert, "recent_not_before_date"))
            # Escalate unknown recent roots.
            if not _has_common_trusted_name(cert):
                suspicious.append(_with_reason(cert, "recent_unknown_root_ca"))
    # Deduplicate by thumbprint.
    uniq: dict[str, dict[str, Any]] = {}
    for row in suspicious:
        thumb = str(row.get("Thumbprint") or f"no_thumb_{len(uniq)}")
        uniq[thumb] = row
    unknown_unique: dict[str, dict[str, Any]] = {}
    for row in unknown_issuers:
        thumb = str(row.get("Thumbprint") or f"no_thumb_{len(unknown_unique)}")
        unknown_unique[thumb] = row
    return {
        "root_certificate_count": len(roots),
        "suspicious_certificates": list(uniq.values()),
        "recent_root_additions": recent,
        "unknown_issuer_candidates": list(unknown_unique.values())[:10],
        "unknown_issuer_candidate_count": unknown_issuer_count,
        "observations": [
            f"Trusted root certificate preview collected: {len(roots)} root certificates.",
            f"Suspicious certificate indicators observed: {len(uniq)}.",
            f"Recent root NotBefore indicators observed: {len(recent)}.",
            f"Unknown issuer/name candidates counted: {unknown_issuer_count}.",
        ],
        "limitations": ["certificate_notbefore_is_validity_start_not_install_time"],
    }

