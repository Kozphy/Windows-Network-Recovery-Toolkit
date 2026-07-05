# Agent deployment — read-only local endpoint agent (Phase 2)

**Status:** MVP — read-only evidence collection and JSONL spool. Not fleet MDM, not signed MSI, not autonomous remediation.

**Related:** [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) · [AGENTS.md](../AGENTS.md) · [agent-workflow-spec.md](agent-workflow-spec.md)

---

## What the agent does

| Capability | Supported |
|------------|-----------|
| Collect normalized endpoint evidence | Yes (via `src/platform_core/evidence_collection/`) |
| Append local JSONL spool | Yes (`.audit/agent-spool.jsonl` default) |
| Report health / spool status | Yes |
| Optional backend `GET /health` probe | Yes (`agent health --api`) |
| Registry mutation | **No** |
| Process kill / firewall reset / adapter disable | **No** |
| Autonomous remediation | **No** |
| Malware / compromise detection | **No** |

**Policy boundary:** `read_only_no_mutation` on every spool event.

---

## CLI commands

Primary entrypoint (unchanged for all other subcommands):

```powershell
python -m windows_network_toolkit agent <subcommand>
```

### One collection cycle

```powershell
python -m windows_network_toolkit agent once
python -m windows_network_toolkit agent once --fixture tests/fixtures/agent/sample_evidence_bundle.json
python -m windows_network_toolkit agent once --spool .audit/demo-agent-spool.jsonl
```

### Loop until Ctrl+C

```powershell
python -m windows_network_toolkit agent run --interval 30
```

For automated tests, `--max-cycles 3` stops after N cycles.

### Health and backend probe

```powershell
python -m windows_network_toolkit agent health
python -m windows_network_toolkit agent health --api http://127.0.0.1:8000
```

When `--api` is set, the agent issues a **read-only** `GET /health` request. It does not call remediation or ingest execute routes.

### Spool inspection

```powershell
python -m windows_network_toolkit agent spool-status
python -m windows_network_toolkit agent spool-status --spool .audit/agent-spool.jsonl
```

---

## Spool format

Default path: `.audit/agent-spool.jsonl` (override with `--spool` or `WNRT_AGENT_SPOOL`).

Each line is one append-only JSON object:

```json
{
  "event_kind": "agent_evidence_collected",
  "endpoint_id": "ep-…",
  "collected_at_utc": "2026-06-12T12:00:00+00:00",
  "read_only": true,
  "automatic_repair": false,
  "remediation_executed": false,
  "policy_boundary": "read_only_no_mutation",
  "blocked_actions": ["ADAPTER_DISABLE", "FIREWALL_RESET", "KILL_PROXY_PROCESS", "WINHTTP_MODIFY"],
  "evidence": { "platform_support_level": "FULL", "observations": [], "limitations": [] }
}
```

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `WNRT_AGENT_SPOOL` | Default spool file path |
| `ENDPOINT_AGENT_API` | Not used by WNRT `agent` CLI — use `agent health --api` instead |

Legacy `python -m endpoint_agent` remains available; it is a **separate** stack with optional HTTP sync to `/platform/ingest/*`. The WNRT `agent` subcommands are the Phase 2 read-only MVP.

---

## Safety boundaries

1. **Observation is not proof** — spool rows are candidate evidence only.
2. **Classification is not accusation** — no malware/compromise labels from the agent.
3. **Recommendation is not execution authority** — `automatic_repair` is always `false`.
4. **Blocked actions** are listed on every event for auditor visibility; the agent never invokes them.
5. **Human-in-the-loop** — remediation stays in `proxy-disable`, `auto-fix-chatgpt`, and platform preview/execute routes with typed confirmation.

---

## Module map

| Path | Role |
|------|------|
| `windows_network_toolkit/agent/read_only.py` | Collection orchestration, health |
| `windows_network_toolkit/agent/spool.py` | JSONL spool read/write/status |
| `src/platform_core/evidence_collection/` | OS abstraction (Phase 1) |
| `windows_network_toolkit/cli.py` | `agent once|run|health|spool-status` |

---

## Verification

```powershell
pytest -q tests/windows_network_toolkit/test_read_only_agent.py
python -m windows_network_toolkit agent once --fixture tests/fixtures/agent/sample_evidence_bundle.json
python -m windows_network_toolkit agent spool-status
```

---

## Explicit non-claims

- Not EDR, antivirus, or MITM detection.
- Not a fleet management or silent repair agent.
- Backend health probe success does **not** authorize remediation.
- Linux/macOS evidence may be `PARTIAL` or `NOT_SUPPORTED` — see evidence_collection limitations.
