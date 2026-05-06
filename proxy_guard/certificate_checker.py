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
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

_SUSPICIOUS_TOKENS = ("mitm", "intercept", "fiddler", "burp", "charles", "proxyman", "packet")
_COMMON_TRUSTED_TOKENS = ("microsoft", "digicert", "globalsign", "let's encrypt", "entrust", "sectigo")


def _run(argv: list[str], timeout_seconds: float = 30.0) -> tuple[int, str]:
    """Execute one certificate-related probe command."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _load_roots() -> list[dict[str, Any]]:
    """Enumerate CurrentUser/LocalMachine root certificate stores.

    Returns:
        list[dict[str, Any]]: Flat certificate records when command succeeds, else empty list.
    """
    ps = (
        "$roots=@(); "
        "$roots += Get-ChildItem Cert:\\CurrentUser\\Root | Select-Object Subject,Issuer,NotBefore,Thumbprint,@{N='Store';E={'CurrentUser'}}; "
        "$roots += Get-ChildItem Cert:\\LocalMachine\\Root | Select-Object Subject,Issuer,NotBefore,Thumbprint,@{N='Store';E={'LocalMachine'}}; "
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


def collect_certificate_indicators() -> dict[str, Any]:
    """Collect root-store signals and suspicious certificate hints.

    Returns:
        dict[str, Any]: Suspicious certificate rows, recent root additions, limitations.

    Constraints:
        "Recently added" uses ``NotBefore`` as an approximation; install time is not directly
        available from this collector.

    Audit Notes:
        Suspicious cert flags are heuristic indicators and should be validated with enterprise PKI
        policy before incident escalation.
    """
    if platform.system().lower() != "windows":
        return {"suspicious_certificates": [], "recent_root_additions": [], "limitations": ["non_windows_platform"]}
    now = datetime.now(timezone.utc)
    suspicious: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    roots = _load_roots()
    for cert in roots:
        subject = str(cert.get("Subject") or "")
        issuer = str(cert.get("Issuer") or "")
        sub_lower = subject.lower()
        iss_lower = issuer.lower()
        if any(t in sub_lower or t in iss_lower for t in _SUSPICIOUS_TOKENS):
            suspicious.append(cert)
        # Heuristic "recently added" approximation from NotBefore when available.
        not_before = str(cert.get("NotBefore") or "")
        try:
            dt = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - dt).days <= 30:
            recent.append(cert)
            # Escalate unknown recent roots.
            if not any(tok in sub_lower or tok in iss_lower for tok in _COMMON_TRUSTED_TOKENS):
                suspicious.append(cert)
    # Deduplicate by thumbprint.
    uniq: dict[str, dict[str, Any]] = {}
    for row in suspicious:
        thumb = str(row.get("Thumbprint") or f"no_thumb_{len(uniq)}")
        uniq[thumb] = row
    return {
        "suspicious_certificates": list(uniq.values()),
        "recent_root_additions": recent,
        "limitations": [],
    }

