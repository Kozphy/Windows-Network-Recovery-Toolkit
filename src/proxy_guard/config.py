"""Runtime configuration for Proxy Guard (env vars, optional JSON file, CLI overrides)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from .policy import ProxyGuardPolicy, load_proxy_guard_policy


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_optional_json_config(path: Path | None) -> dict[str, Any]:
    """Load a JSON object from disk; missing path yields empty dict."""
    if path is None or not path.is_file():
        return {}
    blob = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(blob, dict):
        raise ValueError(f"config root must be an object: {path}")
    return blob


@dataclass(frozen=True)
class ProbeRetrySettings:
    """Subprocess probe retry policy (registry reads)."""

    timeout_seconds: float = 15.0
    max_attempts: int = 3
    backoff_seconds: float = 0.75


@dataclass(frozen=True)
class RollbackLimitSettings:
    """Guards against rollback storms (infinite loops, flapping malware)."""

    cooldown_seconds: float = 60.0
    window_seconds: float = 300.0
    max_rollbacks_per_window: int = 5


@dataclass(frozen=True)
class ProxyGuardServiceConfig:
    """Full service configuration (no argparse types).

    Business logic consumes only this object; CLI builds it via :func:`build_service_config`.
    """

    policy: ProxyGuardPolicy
    jsonl_path: Path
    interval_seconds: float
    once: bool
    auto_rollback: bool
    dry_run_rollback: bool
    run: Callable[..., Any]
    probe: ProbeRetrySettings
    rollback_limits: RollbackLimitSettings
    structured_log_path: Path | None
    exit_after_registry_change_events: int | None = None


def build_service_config(
    *,
    policy: ProxyGuardPolicy,
    jsonl_path: Path,
    interval: float,
    once: bool,
    auto_rollback: bool,
    dry_run_rollback: bool,
    run: Callable[..., Any],
    config_file: Path | None = None,
    structured_log_path: Path | None = None,
    exit_after_registry_change_events: int | None = None,
) -> ProxyGuardServiceConfig:
    """Merge CLI args with optional JSON file and environment variables.

    Precedence for numeric tuning: defaults → JSON file → environment overrides.

    Env vars:
        ``PROXY_GUARD_PROBE_TIMEOUT`` — per ``reg query`` timeout (seconds).
        ``PROXY_GUARD_PROBE_MAX_ATTEMPTS`` — full snapshot retries.
        ``PROXY_GUARD_PROBE_BACKOFF`` — backoff base between attempts (seconds).
        ``PROXY_GUARD_ROLLBACK_COOLDOWN`` — minimum seconds between auto-rollbacks.
        ``PROXY_GUARD_ROLLBACK_WINDOW`` — rolling window for rate limit (seconds).
        ``PROXY_GUARD_ROLLBACK_MAX_PER_WINDOW`` — max auto-rollbacks in window.

    JSON keys (optional file):
        ``probe``: ``{"timeout_seconds", "max_attempts", "backoff_seconds"}``
        ``rollback_limits``: ``{"cooldown_seconds", "window_seconds", "max_rollbacks_per_window"}``
    """
    file_blob = load_optional_json_config(config_file)
    probe_blob = file_blob.get("probe") if isinstance(file_blob.get("probe"), dict) else {}
    rb_blob = file_blob.get("rollback_limits") if isinstance(file_blob.get("rollback_limits"), dict) else {}

    base_timeout = float(probe_blob.get("timeout_seconds", 15.0))
    base_attempts = int(probe_blob.get("max_attempts", 3))
    base_backoff = float(probe_blob.get("backoff_seconds", 0.75))
    probe = ProbeRetrySettings(
        timeout_seconds=_env_float("PROXY_GUARD_PROBE_TIMEOUT", base_timeout),
        max_attempts=_env_int("PROXY_GUARD_PROBE_MAX_ATTEMPTS", base_attempts),
        backoff_seconds=_env_float("PROXY_GUARD_PROBE_BACKOFF", base_backoff),
    )

    base_cool = float(rb_blob.get("cooldown_seconds", 60.0))
    base_win = float(rb_blob.get("window_seconds", 300.0))
    base_max_rb = int(rb_blob.get("max_rollbacks_per_window", 5))
    rollback_limits = RollbackLimitSettings(
        cooldown_seconds=_env_float("PROXY_GUARD_ROLLBACK_COOLDOWN", base_cool),
        window_seconds=_env_float("PROXY_GUARD_ROLLBACK_WINDOW", base_win),
        max_rollbacks_per_window=_env_int("PROXY_GUARD_ROLLBACK_MAX_PER_WINDOW", base_max_rb),
    )

    return ProxyGuardServiceConfig(
        policy=policy,
        jsonl_path=jsonl_path,
        interval_seconds=max(1.0, float(interval)),
        once=once,
        auto_rollback=auto_rollback,
        dry_run_rollback=dry_run_rollback,
        run=run,
        probe=probe,
        rollback_limits=rollback_limits,
        structured_log_path=structured_log_path,
        exit_after_registry_change_events=exit_after_registry_change_events,
    )


def legacy_control_kwargs_to_config(
    *,
    interval: float,
    once: bool,
    auto_rollback: bool,
    policy: ProxyGuardPolicy,
    jsonl_path: Path,
    dry_run_rollback: bool,
    run: Callable[..., Any],
    exit_after_registry_change_events: int | None = None,
) -> ProxyGuardServiceConfig:
    """Map legacy :func:`run_proxy_guard_control` kwargs to :class:`ProxyGuardServiceConfig`."""
    return build_service_config(
        policy=policy,
        jsonl_path=jsonl_path,
        interval=interval,
        once=once,
        auto_rollback=auto_rollback,
        dry_run_rollback=dry_run_rollback,
        run=run,
        config_file=None,
        structured_log_path=None,
        exit_after_registry_change_events=exit_after_registry_change_events,
    )


def merge_config_overrides(base: ProxyGuardServiceConfig, **overrides: Any) -> ProxyGuardServiceConfig:
    """Return a copy with dataclass fields replaced (tests)."""
    return replace(base, **overrides)
