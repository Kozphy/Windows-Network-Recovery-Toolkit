# Agent (legacy remote diagnose loop)

**Status:** Legacy SaaS demo agent — distinct from the **read-only local agent** in `windows_network_toolkit/agent/`.

| Agent | Entry | Mutates endpoint? | Sends data to |
|-------|-------|-------------------|---------------|
| **Read-only (preferred)** | `python -m windows_network_toolkit agent *` | **No** | Local JSONL spool only |
| **Legacy (this folder)** | `python agent/agent.py` | Can trigger backend `/diagnose` flows | Remote FastAPI + Supabase JWT |

For portfolio hardening and audit defense, prefer the read-only agent documented in [docs/agent-deployment.md](../docs/agent-deployment.md).

---

## Legacy agent — run once

```bash
pip install -r requirements.txt
python agent/agent.py --api http://localhost:8000 --token <SUPABASE_ACCESS_TOKEN> --project-id <PROJECT_ID>
```

## Loop mode

```bash
python agent/agent.py --api http://localhost:8000 --token <SUPABASE_ACCESS_TOKEN> --project-id <PROJECT_ID> --loop --interval 10
```

## What it collects (read-only probes)

- ping
- DNS
- HTTPS
- proxy state
- TIME_WAIT / ESTABLISHED

## Side effects

- **Network:** HTTP POST to configured API (`/diagnose`, `/monitor`)
- **Local:** Probe subprocesses; no registry mutation from this script alone
- **Remote:** May increment usage metering when SaaS backend is enabled

## Safety boundaries

- Does **not** replace `windows_network_toolkit` policy gates or typed confirmation for remediation.
- Bearer token must be treated as a secret — do not commit tokens to git.
- This agent is **not** required for offline pytest or fixture replay demos.

## Audit notes

Correlate backend `/history` or database rows with agent loop timestamps. For governance JSONL demos, use fixture audit dirs under `tests/fixtures/risk_analytics/` instead of live agent traffic.
