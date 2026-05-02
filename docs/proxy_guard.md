# Proxy Guard

Proxy Guard reads **HKCU** `Internet Settings` (`ProxyEnable`, `ProxyServer`, `AutoConfigURL`, `AutoDetect`), normalizes `ProxyServer` strings, correlates LISTENING `netstat` rows, optionally enriches via `Win32_Process` (through PowerShell/`Get-CimInstance`), emits JSONL audits, and offers a typed-phrase-guarded disable path (`DISABLE_PROXY`) that edits only WinINET user keys.

## Commands

```powershell
python -m src proxy-status
python -m src proxy-status --json
python -m src proxy-owner [--port N] [--json]
python -m src proxy-monitor [--interval 5] [--once] [--jsonl logs/proxy_guard_events.jsonl]
python -m src proxy-guard [--interval 5] [--once] [--auto-rollback] [--policy PATH] [--jsonl PATH] [--config shared/proxy_guard_service.config.example.json] [--structured-log logs/proxy_guard_service.jsonl]
python -m src proxy-disable [--dry-run] [--clear-server]
```

## Proxy Guard control plane (`proxy-guard`)

**Purpose:** Near–real-time polling of the same HKCU keys as `proxy-monitor`, plus:

- **Attribution:** For localhost proxy ports, resolve **port → netstat → PID → process name** (same stack as `proxy-owner`).
- **Policy:** JSON whitelist (`allowed_process_name_substrings`, `allowed_process_names_exact`); **default deny** for unknown processes.
- **Automatic rollback (opt-in):** Only when `--auto-rollback` is set and the decision is **blocked**, the toolkit runs the **low-risk** bundle:
  - HKCU WinINET disable (`ProxyEnable=0`, optional `ProxyServer` delete) via `reg.exe`
  - `netsh winhttp reset proxy` for WinHTTP

No firewall, routing, adapter, or certificate mutations are performed automatically.

### Target architecture (modules)

| Module | Role |
|--------|------|
| `src/proxy_guard/registry.py` | HKCU reads via `reg query` (configurable per-query timeout) |
| `src/proxy_guard/probes.py` | Retry/backoff wrapper for full snapshot reads |
| `src/proxy_guard/parser.py` | Deterministic `ProxyServer` parse |
| `src/proxy_guard/planning.py` | Pure registry view helpers (no I/O) |
| `src/proxy_guard/owner.py` | Localhost port attribution |
| `src/proxy_guard/watcher.py` | Read-only polling + legacy JSONL |
| `src/proxy_guard/policy.py` | Whitelist load + `PolicyDecision` |
| `src/proxy_guard/rollback.py` | Idempotent WinINET + WinHTTP rollback executor |
| `src/proxy_guard/rollback_limits.py` | Cooldown + sliding-window rate limit (anti-loop) |
| `src/proxy_guard/service.py` | Control loop: probes → policy → optional rollback → audit |
| `src/proxy_guard/control.py` | Shim exporting legacy `run_proxy_guard_control` |
| `src/proxy_guard/config.py` | `ProxyGuardServiceConfig` (JSON file + env) |
| `src/proxy_guard/structured_log.py` | JSON-lines operational logging |
| `src/proxy_guard/events.py` | `proxy_guard_control_event` JSONL rows |

### Configuration and environment

Optional JSON (see `shared/proxy_guard_service.config.example.json`) passed via `--config`:

- `probe`: `timeout_seconds`, `max_attempts`, `backoff_seconds` for `reg query` reads.
- `rollback_limits`: `cooldown_seconds` (min gap between auto-rollbacks), `window_seconds` + `max_rollbacks_per_window` (sliding cap).

Environment overrides (after defaults + JSON file):

| Variable | Purpose |
|----------|---------|
| `PROXY_GUARD_PROBE_TIMEOUT` | Per-`reg query` timeout (seconds) |
| `PROXY_GUARD_PROBE_MAX_ATTEMPTS` | Full snapshot retries |
| `PROXY_GUARD_PROBE_BACKOFF` | Backoff base between attempts |
| `PROXY_GUARD_ROLLBACK_COOLDOWN` | Cooldown after each rollback |
| `PROXY_GUARD_ROLLBACK_WINDOW` | Rolling window for rollback count |
| `PROXY_GUARD_ROLLBACK_MAX_PER_WINDOW` | Max rollbacks in that window |

### Structured operational logs

`src/proxy_guard/structured_log.py` writes one JSON object per line to **stderr** and, if `--structured-log PATH` is set, duplicates the same line to that file. Stable keys: `schema_version`, `timestamp`, `logger` (`proxy_guard.service`), `level`, `event`, plus context fields (`duration_ms`, `probe_notes`, etc.).

This is separate from **audit** JSONL (`--jsonl`): operational logs are for SRE triage; audit JSONL is the compliance-oriented control-plane record.

### Unsafe operations (manual review)

| Risk | Mitigation |
|------|------------|
| `--auto-rollback` + `netsh winhttp reset proxy` | Resets **WinHTTP** system proxy; can disrupt apps using WinHTTP until reconfigured. Opt-in; logged in JSONL. |
| HKCU `reg` mutations | Affects **current user** WinINET only; reversible via UI or `proxy-disable`-style commands; may race with policy-enforcing software. |
| Default deny + wrong whitelist | Legitimate tools may be blocked; tune policy and use `allow_when_attribution_empty` only with care. |
| Attribution gaps | `netstat`/CIM can miss or mis-label owners; decisions may be conservative (blocked). |

### Rollback idempotency and loop prevention

- **Idempotent:** Re-running WinINET disable (`ProxyEnable=0`) and `ProxyServer` delete is safe to repeat. `netsh winhttp reset proxy` is safe to repeat. When HKCU already shows proxy off and server empty, WinINET `reg` steps are **skipped** but WinHTTP reset may still run (`rollback_detail.wininet_skipped_already_cleared`).
- **No infinite rollback loop:** After each rollback, a **cooldown** blocks further auto-rollbacks; a **sliding window** caps rollbacks per interval. When limits trip, the audit row uses `action: "suppressed"` and `rollback_suppressed_reason` instead of executing another rollback.

### Folder layout (`src/proxy_guard/`)

```
proxy_guard/
  __init__.py
  service.py      # Main control loop
  control.py      # Legacy shim -> service
  config.py       # Service config (probe + rollback limits)
  probes.py       # Registry read retries
  planning.py     # Pure view helpers
  rollback_limits.py
  structured_log.py
  events.py       # JSONL factories (monitor + control-plane)
  owner.py        # Attribution
  parser.py
  policy.py       # Whitelist / default deny
  registry.py
  remediation.py  # WinINET reg argv builders
  rollback.py     # apply_mutations + netsh winhttp
  watcher.py      # Read-only monitor
```

### Example control-plane JSONL (`logs/proxy_guard_control.jsonl`)

One line (pretty-printed for review):

```json
{
  "type": "proxy_guard_control",
  "event_type": "registry_change",
  "timestamp": "2026-05-02T12:00:00.000000+00:00",
  "previous_registry_view": {
    "proxy_enable": 0,
    "proxy_server": null,
    "auto_config_url": null,
    "auto_detect": 0,
    "parsed": {}
  },
  "current_registry_view": {
    "proxy_enable": 1,
    "proxy_server": "127.0.0.1:8080",
    "auto_config_url": null,
    "auto_detect": 0,
    "parsed": {
      "raw": "127.0.0.1:8080",
      "is_localhost_proxy": true,
      "localhost_port": 8080
    }
  },
  "attribution": {
    "port": 8080,
    "owners": [{ "pid": 999, "process_name": "example.exe" }],
    "notes": []
  },
  "policy": { "source_path": "C:\\\\...\\\\shared\\\\proxy_guard_policy.example.json" },
  "decision": "blocked",
  "decision_detail": "no_whitelist_match_default_deny",
  "action": "rollback",
  "matched_rule": null,
  "primary_process_name": "example.exe",
  "rollback_detail": {
    "wininet_reg": [{ "argv": ["reg", "add", "..."], "returncode": 0, "stdout": "", "stderr": "" }],
    "winhttp_reset": { "argv": ["netsh", "winhttp", "reset", "proxy"], "returncode": 0, "stdout": "", "stderr": "" }
  },
  "post_rollback_registry_view": {
    "proxy_enable": 0,
    "proxy_server": null,
    "auto_detect": 0,
    "parsed": {}
  }
}
```

### Safety model

| Area | Allowed automatically | Blocked / manual |
|------|----------------------|------------------|
| Detection | Polling HKCU Internet Settings | — |
| Attribution | Best-effort netstat/CIM | Perfect attribution (OS limits apply) |
| Policy | Whitelist match on resolved `process_name` | Everything else (default deny) |
| Rollback | **Only** when `--auto-rollback` and decision **blocked**; uses **only** WinINET HKCU disable + `netsh winhttp reset proxy` | Firewall, DNS, adapters, certs, machine-wide proxy policy |
| Audit | Append-only JSONL under `logs/` | — |

**Rollback guarantees:** Mutations are the same reversible primitives documented for `proxy-disable` plus WinHTTP reset. Operators can re-enable proxies manually or via trusted tooling; policy may reapply corporate settings after sync/logon.

### Future extensibility

- **ETW / registry callbacks:** Replace polling with filtered notifications for lower latency (same policy + rollback surface).
- **Multi-endpoint agent:** Ship control loop + JSONL forwarder; centralize policy distribution (still no cloud telemetry required).
- **Metrics:** Expose counters (changes/min, blocked rollbacks) via local Prometheus-compatible textfile or Windows Performance Counters.

## Logs

Append-only sinks (local):

- `logs/proxy_guard_events.jsonl` (`proxy-monitor`)
- `logs/proxy_guard_control.jsonl` (`proxy-guard`)
- `logs/repair_audit.jsonl` after successful `proxy-disable`

## Audit notes

Changing proxy disables the software that originally set the keys unless that software is addressed separately.
