# Archived portfolio labs

Packages here are **out of the mainline portfolio path** but preserved in git history
on branch `refactor/portfolio-cleanup` (pre-cleanup tag: `portfolio-pre-cleanup-v1`).

They are excluded from pytest collection (`pytest.ini` `norecursedirs`).

| Package | Former role |
|---------|-------------|
| `network_agent/` | Alternate FastAPI hybrid agent demo |
| `hybrid_frontend/` | Static UI for `network_agent` |
| `labs/` | Index of experimental demos |
| `agent/` | Legacy classify / plan / execute agent |
| `order_flow_simulator/` | Fintech FSM demo |
| `edge_device/` | AI-edge simulation (`edge-diagnose` CLI) |
| `mcp_server/` | Optional MCP stdio tools |
| `proxy_attribution/` | Standalone attribution CLI |
| `src/market_events/` | Macro/crypto research signals CLI |
| `tests/` | Suites that only covered the above |

To exercise an archived package locally, add `archive/` (and `archive/src` parents) to
`PYTHONPATH` and run its module entrypoint. Prefer mainline:

- `python -m windows_network_toolkit`
- `python -m src`
- `wnrt-api` / NiceGUI dashboard / Power BI under `analytics/`

See `docs/portfolio-cleanup-inventory.md`.
