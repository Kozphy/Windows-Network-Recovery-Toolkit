# Labs — portfolio experiments (not mainline)

The **Endpoint Reliability Platform** mainline detects and explains Windows proxy/browser-path failures with policy-gated remediation previews.

These directories are **experimental** or teaching artifacts. They reuse similar patterns (observation → policy → audit) but are **not** the primary product story.

| Path | Topic | Entry |
|------|-------|-------|
| `edge_device/` | AI-edge simulation | `python -m src edge-diagnose --fixture tests/fixtures/edge/healthy.json` |
| `src/market_events/` | Macro/crypto research signals | `python -m src.market_events calendar` |
| `platform_core/decision_platform/` | Multi-domain adapters | `pytest tests/decision_platform` |
| `backend/decision_intelligence/` | Generic decision API | `/decision-intelligence/*` |
| `platform_core/outcome_learning/` | Post-decision learning | `pytest tests/outcome_learning` |
| `order_flow_simulator/` | Event-sourcing FSM demo | See module README |

For interviews, lead with the mainline story in the root README and `docs/interview_case_study_tier1.md`.
