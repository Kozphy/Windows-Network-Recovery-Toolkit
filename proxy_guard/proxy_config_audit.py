"""Read-only proxy configuration audit across WinINET, WinHTTP, Git, npm, env, and browser policy.

This module never mutates any system state. It produces a structured ``proxy_config_checks``
mapping plus a ``findings`` list classifying drift between Windows-level proxy posture and
developer-tool proxy posture (``windows_proxy_drift``, ``git_proxy_drift``, ``npm_proxy_drift``,
``browser_policy_proxy``, ``wininet_winhttp_mismatch``, ``dev_tool_proxy_mismatch``).

Heuristic attribution boundary:
    Findings are observation-level only. They surface drift surfaces but do not prove which
    actor wrote any of the values. For writer attribution, see
    :mod:`evidence.registry_writer_proof`.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

try:
    # Hoisted from inside ``collect_wininet_proxy`` per the workspace
    # no-inline-imports rule. The collector module is stdlib-only at import
    # time (subprocess/platform/etc.); Windows-only behavior is gated at
    # call time via ``platform.system()``. We keep the try/except so this
    # module still imports if the symbol is ever moved or renamed.
    from proxy_guard.proxy_signal_collector import collect_proxy_signals as _collect_proxy_signals
except Exception:  # noqa: BLE001 — defensive: keep audit usable if collector breaks
    _collect_proxy_signals = None  # type: ignore[assignment]

PROXY_ENV_VARS: tuple[str, ...] = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "ALL_PROXY",
    "all_proxy",
)

GIT_PROXY_KEYS: tuple[str, ...] = ("http.proxy", "https.proxy")
NPM_PROXY_KEYS: tuple[str, ...] = ("proxy", "https-proxy", "registry")
BROWSER_POLICY_REG_KEYS: tuple[tuple[str, str, str], ...] = (
    (r"HKCU\Software\Policies\Google\Chrome", "ProxyServer", "chrome_user"),
    (r"HKLM\Software\Policies\Google\Chrome", "ProxyServer", "chrome_machine"),
    (r"HKCU\Software\Policies\Microsoft\Edge", "ProxyServer", "edge_user"),
    (r"HKLM\Software\Policies\Microsoft\Edge", "ProxyServer", "edge_machine"),
)

Status = str  # "ok" | "configured" | "unset" | "unknown" | "warning"


@dataclass(frozen=True)
class ProxyFinding:
    """A drift / mismatch observation produced by the audit.

    Attributes:
        kind: Stable identifier for downstream policy / dashboard mapping.
        status: ``ok``, ``warning``, or ``info``. Findings never claim ``proof``.
        evidence_level: Always ``observation``; this module never claims proof.
        reason: Short human-readable explanation derived from the snapshot.
    """

    kind: str
    status: str
    evidence_level: str = "observation"
    reason: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "status": self.status,
            "evidence_level": self.evidence_level,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProxyConfigCheckResult:
    """Structured result returned by :func:`build_proxy_config_audit`."""

    proxy_config_checks: dict[str, Any]
    findings: list[ProxyFinding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proxy_config_checks": self.proxy_config_checks,
            "findings": [f.to_dict() for f in self.findings],
            "limitations": list(self.limitations),
        }


RunFn = Callable[..., Any]


def _safe_run(
    argv: list[str],
    *,
    run: RunFn,
    timeout: float = 5.0,
) -> tuple[int, str, str]:
    """Run an external command without shell expansion. Return ``(rc, stdout, stderr)``.

    On any OS error or timeout returns ``(-1, "", str(exc))`` so callers stay alive.
    """

    try:
        proc = run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, "", f"{type(exc).__name__}:{exc}"
    return int(getattr(proc, "returncode", 1)), str(getattr(proc, "stdout", "") or ""), str(getattr(proc, "stderr", "") or "")


def _which(executable: str) -> str | None:
    """Return absolute path of ``executable`` if present on ``PATH``."""
    return shutil.which(executable)


def collect_environment_proxies(
    env: Mapping[str, str] | None = None,
    *,
    names: Iterable[str] = PROXY_ENV_VARS,
) -> dict[str, str | None]:
    """Read proxy-related environment variables.

    Args:
        env: Optional environment mapping for testability. Defaults to ``os.environ``.
        names: Variable names to read.

    Returns:
        Mapping of variable name to value. Unset variables return ``None`` (not removed)
        so the audit shape stays stable for the dashboard.
    """

    src = env if env is not None else os.environ
    return {name: (src.get(name) if name in src else None) for name in names}


def collect_git_proxy(
    *,
    run: RunFn = subprocess.run,
    git_executable: str | None = None,
) -> dict[str, Any]:
    """Read git global proxy configuration without mutating it.

    Returns:
        Mapping with ``available``, ``values``, and ``limitations`` keys.
        ``values`` includes ``http.proxy`` and ``https.proxy`` as strings; missing keys map to ``None``.
    """

    git = git_executable or _which("git")
    if not git:
        return {
            "available": False,
            "values": {key: None for key in GIT_PROXY_KEYS},
            "limitations": ["git executable not found on PATH"],
        }
    out: dict[str, str | None] = {}
    limitations: list[str] = []
    for key in GIT_PROXY_KEYS:
        rc, stdout, _stderr = _safe_run([git, "config", "--global", "--get", key], run=run)
        if rc == 0:
            out[key] = stdout.strip() or None
        elif rc == 1:
            out[key] = None
        else:
            out[key] = None
            limitations.append(f"git config read failed for {key}")
    return {"available": True, "values": out, "limitations": limitations}


def collect_npm_proxy(
    *,
    run: RunFn = subprocess.run,
    npm_executable: str | None = None,
) -> dict[str, Any]:
    """Read npm proxy configuration without mutating it.

    npm prints the literal ``null`` for unset values; this normalizer maps that to ``None``.
    """

    npm = npm_executable or _which("npm") or _which("npm.cmd")
    if not npm:
        return {
            "available": False,
            "values": {key: None for key in NPM_PROXY_KEYS},
            "limitations": ["npm executable not found on PATH"],
        }
    out: dict[str, str | None] = {}
    limitations: list[str] = []
    for key in NPM_PROXY_KEYS:
        rc, stdout, stderr = _safe_run([npm, "config", "get", key], run=run)
        if rc != 0:
            out[key] = None
            limitations.append(f"npm config get {key} failed: {stderr.strip()[:160]}")
            continue
        value = stdout.strip()
        out[key] = None if value.lower() in {"null", "undefined", ""} else value
    return {"available": True, "values": out, "limitations": limitations}


def collect_winhttp_proxy(*, run: RunFn = subprocess.run) -> dict[str, Any]:
    """Snapshot WinHTTP proxy via ``netsh winhttp show proxy`` (read-only)."""

    if platform.system().lower() != "windows":
        return {
            "available": False,
            "raw": "",
            "direct_access": None,
            "limitations": ["netsh winhttp not available on non-Windows"],
        }
    rc, stdout, stderr = _safe_run(["netsh", "winhttp", "show", "proxy"], run=run, timeout=8.0)
    text = stdout.strip()
    if rc != 0:
        return {
            "available": False,
            "raw": text,
            "direct_access": None,
            "limitations": [f"netsh winhttp returned {rc}: {stderr.strip()[:200]}"],
        }
    direct = "direct access" in text.lower() or "no proxy server" in text.lower()
    return {
        "available": True,
        "raw": text[:2000],
        "direct_access": bool(direct),
        "limitations": [],
    }


def collect_wininet_proxy() -> dict[str, Any]:
    """Snapshot WinINET HKCU proxy posture using existing local-first collector."""

    if _collect_proxy_signals is None:
        return {
            "available": False,
            "values": {
                "ProxyEnable": None,
                "ProxyServer": None,
                "AutoConfigURL": None,
                "ProxyOverride": None,
            },
            "limitations": ["wininet collector unavailable: import failed"],
        }
    try:
        signals = _collect_proxy_signals()
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "values": {
                "ProxyEnable": None,
                "ProxyServer": None,
                "AutoConfigURL": None,
                "ProxyOverride": None,
            },
            "limitations": [f"wininet collector raised: {type(exc).__name__}"],
        }
    return {
        "available": True,
        "values": {
            "ProxyEnable": signals.get("proxy_enable"),
            "ProxyServer": signals.get("proxy_server"),
            "AutoConfigURL": signals.get("auto_config_url"),
            "ProxyOverride": signals.get("proxy_override"),
            "AutoDetect": signals.get("auto_detect"),
        },
        "limitations": list(signals.get("limitations") or []),
    }


def collect_browser_policy_proxy(*, run: RunFn = subprocess.run) -> dict[str, Any]:
    """Read browser policy proxy registry keys for Chrome/Edge.

    Strictly read-only via ``reg query``. Missing keys return ``None``; permission errors
    record a limitation rather than crash.
    """

    if platform.system().lower() != "windows":
        return {
            "available": False,
            "values": {label: None for _, _, label in BROWSER_POLICY_REG_KEYS},
            "limitations": ["browser policy registry keys are Windows-only"],
        }
    values: dict[str, str | None] = {}
    limitations: list[str] = []
    for key, value_name, label in BROWSER_POLICY_REG_KEYS:
        rc, stdout, stderr = _safe_run(["reg", "query", key, "/v", value_name], run=run, timeout=4.0)
        if rc != 0:
            values[label] = None
            err = stderr.strip().lower()
            if err and "unable to find" not in err and "cannot find" not in err:
                limitations.append(f"reg query {label} failed: {stderr.strip()[:160]}")
            continue
        parsed: str | None = None
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped or value_name.lower() not in stripped.lower():
                continue
            tokens = [tok for tok in stripped.split(None) if tok]
            if len(tokens) >= 3:
                parsed = " ".join(tokens[2:])
                break
        values[label] = parsed
    return {"available": True, "values": values, "limitations": limitations}


def _looks_like_localhost(value: str) -> bool:
    lowered = value.lower()
    return "127.0.0.1" in lowered or "localhost" in lowered or "::1" in lowered


def classify_findings(checks: dict[str, Any]) -> list[ProxyFinding]:
    """Compare collected sub-results and emit drift findings.

    The classifier is intentionally conservative:
    * It never claims malicious intent.
    * It never recommends mutation; consumers must use the policy gate.
    """

    findings: list[ProxyFinding] = []
    wininet = checks.get("wininet") or {}
    winhttp = checks.get("winhttp") or {}
    git = checks.get("git") or {}
    npm = checks.get("npm") or {}
    env = checks.get("environment") or {}
    browser_policy = checks.get("browser_policy") or {}

    win_values = wininet.get("values") or {}
    proxy_enable = win_values.get("ProxyEnable")
    proxy_server = str(win_values.get("ProxyServer") or "")
    auto_config = win_values.get("AutoConfigURL")
    win_active = bool(proxy_enable in (1, "1", True)) or bool(proxy_server) or bool(auto_config)

    if proxy_server and _looks_like_localhost(proxy_server):
        findings.append(
            ProxyFinding(
                kind="windows_proxy_drift",
                status="warning",
                reason=f"WinINET ProxyServer={proxy_server} routes browser traffic through a localhost listener.",
            )
        )

    direct_access = winhttp.get("direct_access")
    if win_active and direct_access is True:
        findings.append(
            ProxyFinding(
                kind="wininet_winhttp_mismatch",
                status="warning",
                reason="WinINET shows an enabled proxy while WinHTTP reports direct access.",
            )
        )

    git_values = git.get("values") or {}
    git_proxy = git_values.get("http.proxy") or git_values.get("https.proxy")
    if git_proxy and not win_active:
        findings.append(
            ProxyFinding(
                kind="git_proxy_drift",
                status="warning",
                reason=f"Git proxy is set ({git_proxy}) while Windows proxy posture is disabled.",
            )
        )
    if git_proxy and win_active and proxy_server and git_proxy not in proxy_server:
        findings.append(
            ProxyFinding(
                kind="dev_tool_proxy_mismatch",
                status="warning",
                reason=f"Git proxy ({git_proxy}) does not match Windows ProxyServer ({proxy_server}).",
            )
        )

    npm_values = npm.get("values") or {}
    npm_proxy = npm_values.get("https-proxy") or npm_values.get("proxy")
    if npm_proxy and not win_active:
        findings.append(
            ProxyFinding(
                kind="npm_proxy_drift",
                status="warning",
                reason="npm https-proxy is set while Windows proxy is disabled.",
            )
        )

    env_lower = {k.lower(): v for k, v in env.items() if v}
    env_https = env_lower.get("https_proxy") or env_lower.get("http_proxy")
    if env_https and not win_active:
        findings.append(
            ProxyFinding(
                kind="env_proxy_drift",
                status="info",
                reason="HTTPS_PROXY/HTTP_PROXY environment variables are set while Windows proxy is disabled.",
            )
        )

    bp_values = browser_policy.get("values") or {}
    if any(bp_values.values()):
        findings.append(
            ProxyFinding(
                kind="browser_policy_proxy",
                status="info",
                reason="Browser policy registry keys configure a proxy; do not modify policy keys without operator confirmation.",
            )
        )

    return findings


def build_proxy_config_audit(
    *,
    run: RunFn = subprocess.run,
    env: Mapping[str, str] | None = None,
) -> ProxyConfigCheckResult:
    """Run all read-only sub-collectors and classify drift findings.

    Args:
        run: Subprocess runner injected by tests.
        env: Optional environment mapping for testability.
    """

    wininet = collect_wininet_proxy()
    winhttp = collect_winhttp_proxy(run=run)
    git = collect_git_proxy(run=run)
    npm = collect_npm_proxy(run=run)
    environment = collect_environment_proxies(env=env)
    browser_policy = collect_browser_policy_proxy(run=run)

    checks = {
        "wininet": wininet,
        "winhttp": winhttp,
        "git": git,
        "npm": npm,
        "environment": environment,
        "browser_policy": browser_policy,
    }
    limitations: list[str] = []
    for sub in (wininet, winhttp, git, npm, browser_policy):
        for note in sub.get("limitations") or []:
            if note:
                limitations.append(str(note))
    findings = classify_findings(checks)
    return ProxyConfigCheckResult(
        proxy_config_checks=checks,
        findings=findings,
        limitations=list(dict.fromkeys(limitations)),
    )
