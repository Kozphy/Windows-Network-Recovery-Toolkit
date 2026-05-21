# Localhost proxy drift investigation workflow

Read-only investigation package: **`src/proxy_investigation/`**

## Purpose

Produce a structured incident report when WinINET enables an unexpected **localhost** proxy (common with Node/Electron/dev tooling) without claiming registry-writer proof or malware intent.

## Principle

**Observation ≠ Inference ≠ Proof**

| Layer | Examples in this workflow |
| --- | --- |
| Observation | `ProxyEnable=1`, `ProxyServer=127.0.0.1:port`, listener PID rows |
| Inference | Ranked `Hypothesis` titles ("dev proxy path appears operational") |
| Proof | Not claimed by default — Sysmon/registry-writer telemetry is out of scope unless added upstream |

## Pipeline

```
collect_proxy_state → collect_listener_evidence → collect_dev_process_correlation
        → run_validation → build_hypotheses → render_incident_report
        → optional append_investigation + reports/proxy_investigations/<run_id>.md
```

Entry point (Windows, from repo root):

```powershell
python -c "from pathlib import Path; from src.proxy_investigation import run_proxy_investigation; r = run_proxy_investigation(repo_root=Path('.')); print(r.primary_hypothesis_id); print(r.human_report[:500])"
```

There is **no** dedicated `python -m src` subcommand yet — use the module API above or wire your own wrapper.

## Outputs

| Artifact | Path |
| --- | --- |
| JSONL audit row | `logs/proxy_investigation.jsonl` |
| Markdown report | `reports/proxy_investigations/<run_id>.md` |
| In-memory result | `ProxyInvestigationResult` (`run_id`, hypotheses, limitations) |

## Safety boundaries

- **Read-only** on the investigation path: no proxy disable, no process kill, no cert deletion.
- Remediation catalog rows are **preview-only**; `kill_process` and `delete_certificates` are **`BLOCK`**.
- Attribution is **listener correlation** unless extended with writer-proof telemetry elsewhere.

## Relationship to other modules

| Module | Role |
| --- | --- |
| `src.proxy_guard` | Live collectors, `proxy disable`, snapshots, guard watch JSONL |
| `proxy_reasoning/` | Canonical scenario + policy pipeline with replay audit (`logs/proxy_reasoning_audit.jsonl`) |
| `python -m src diagnose --live` | Fleet-style hypotheses + proof engine for operator CLIs |

Use **investigation** for a single markdown incident narrative; use **proxy_reasoning** for policy-gated action evaluation on collector payloads; use **`diagnose --live`** for the main toolkit decision JSON.

## Failure modes

| Symptom | Likely cause | Recovery |
| --- | --- | --- |
| Validation/probe exceptions | Registry/subprocess failure on non-Windows or blocked `reg` | Run on Windows elevated user; check `validation.py` inputs |
| Empty hypotheses | Proxy disabled or non-loopback server | Confirm `proxy-status` / registry |
| `listener_correlation` but unknown writer | Expected limitation | Enable Sysmon/registry auditing; compare `proxy-watch` JSONL |
| Large JSONL growth | Repeated investigations | Archive `logs/proxy_investigation.jsonl` locally |

## Audit notes for reviewers

- Correlate `run_id` between JSONL and `reports/proxy_investigations/*.md`.
- `human_report_excerpt` in JSONL is truncated to 2000 characters — read the markdown file for full text.
- `MALWARE_FORBIDDEN` and `ATTRIBUTION_LISTENER_ONLY` strings must appear in limitations — do not strip for external reports without review.

## Remediation (operator, separate step)

After preview review:

```powershell
python -m src proxy disable
python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY --soak-minutes 15
```

See [`proxy_green_definition.md`](proxy_green_definition.md) and [`cli_reference.md`](cli_reference.md).
