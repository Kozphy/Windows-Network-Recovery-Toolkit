# MCP Tool Specification

Read-only Model Context Protocol tools for technology risk evidence.

## Server

- Entry: `python -m mcp_server`
- Transport: stdio
- Env: `MCP_READ_ONLY=1` (default) — writes rejected

## Tools

| Tool | Parameters | Returns | Backing |
|------|------------|---------|---------|
| `get_proxy_status` | `fixture_path?` | Proxy state dict | Fixture or shape from proxy-status |
| `get_tls_status` | `host`, `port?` | TLS path summary | `src/platform_core/tls/engine.py` |
| `get_risk_report` | `limit?` | Risk items list | Incident projector / DB |
| `get_evidence_timeline` | `aggregate_id` | Domain events | `src/platform_core/events/projector.py` |
| `run_control_tests` | `incident_id` | Control results (read-only) | DB control_tests |
| `generate_governance_report` | `audit_dir?` | Executive KPI dict | `build_executive_report` |

## Audit

Every invocation appends `McpToolInvoked` to domain event log with:

- `tool_name`, `params_hash`, `actor`, `read_only: true`

## Policy gate

- No `remediate`, `execute`, or `ingest` tools in Phase 3
- Future write tools require explicit `MCP_READ_ONLY=0` + policy check (not implemented)
