.PHONY: test lint typecheck demo demo-api demo-tier1 demo-production demo-healthy demo-proxy-drift demo-final-causation replay-fixtures install verify-lint verify-format portfolio-test proxy-intermittent prod-demo-up prod-demo-down prod-demo-health prod-demo-benchmark prod-demo-report fix-proxy fix-chatgpt

WATCH_MINUTES ?= 15

PYTHON ?= python
ifeq ($(OS),Windows_NT)
ifneq (,$(wildcard .venv/Scripts/python.exe))
PYTHON := .venv/Scripts/python.exe
endif
else
ifneq (,$(wildcard .venv/bin/python))
PYTHON := .venv/bin/python
endif
endif
PYTEST ?= $(PYTHON) -m pytest
install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTEST) -q

portfolio-test:
	$(PYTEST) -q tests/test_portfolio_case_studies.py

principles-test:
	$(PYTEST) -q tests/test_observation_not_proof.py tests/test_correlation_not_causation.py tests/test_confidence_not_certainty.py tests/test_policy_not_safety.py tests/test_cs1_principle_compliance.py

lint:
	ruff check .

verify-lint:
	ruff check .

verify-format:
	black --check .

typecheck:
	mypy src/platform_core/ai_risk_analyst src/platform_core/risk src/platform_core/governance src/platform_core/analytics --ignore-missing-imports

# Golden read-only demo: replay proxy_drift fixture, policy, markdown report.
demo:
	$(PYTHON) scripts/golden_demo.py
	$(PYTEST) -q windows_network_toolkit/tests/test_replay.py tests/test_demo_replay_pipeline.py

# Auto-fix dead localhost WinINET proxy (Windows, no prompts)
fix-proxy:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/auto-fix-proxy.ps1

fix-chatgpt:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/auto-fix-chatgpt.ps1

# Starts API in fixture mode (requires uvicorn; blocks terminal).
demo-api:
	PLATFORM_FIXTURE_MODE=1 $(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Read-only fixture pipeline (same steps as scripts/demo_tier1.ps1).
demo-tier1:
	$(PYTHON) -m src diagnose --fixture tests/fixtures/features_healthy_signals.json
	$(PYTHON) -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json
	$(PYTHON) -m src proxy-report --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) tools/public_release_audit.py --tracked-only
	$(PYTEST) -q tests/test_policy_safety_contract.py tests/test_api_dry_run_default.py tests/test_replay_determinism.py tests/test_audit_contract.py tests/test_evidence_level_contract.py tests/test_safety_contract_extensions.py tests/test_fixture_regression_demo.py

# Production-shaped portfolio demo (fixtures + case studies + fleet sim; no destructive actions).
demo-production:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/demo_production.ps1

demo-healthy:
	$(PYTHON) -m src demo-scenario healthy --format both

demo-proxy-drift:
	$(PYTHON) -m src demo-scenario proxy-drift --format both

# Live Windows soak: baseline -> timed proxy-watch -> report/investigate/attribution (read-only).
proxy-intermittent:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/proxy_guard/run_intermittent_check.ps1 -WatchMinutes $(WATCH_MINUTES)

demo-final-causation:
	$(PYTHON) -m src demo-scenario final-causation --format both

demo-fleet-enterprise:
	$(PYTHON) -m platform_core.demo_fleet --endpoints 100 --incidents 20 --output platform_data_fleet_demo

replay-fixtures:
	$(PYTHON) -m src demo-scenario healthy --format both
	$(PYTHON) -m src demo-scenario proxy-drift --format both
	$(PYTHON) -m src demo-scenario final-causation --format both
	$(PYTHON) -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json
	$(PYTEST) -q tests/test_demo_replay_pipeline.py tests/test_replay_determinism.py

# Reviewer Docker Demo (Option C) — minimal API, DEMO_MODE, fixture-backed
demo-up:
	docker compose -f docker-compose.demo.yml up --build -d

demo-down:
	docker compose -f docker-compose.demo.yml down

demo-health:
	curl -sf http://127.0.0.1:8000/health

demo-dead-proxy:
	$(PYTHON) -m windows_network_toolkit proxy-status --fixture fixtures/proxy/dead-localhost-proxy.json

demo-mismatch:
	$(PYTHON) -m windows_network_toolkit proxy-status --fixture fixtures/proxy/wininet-winhttp-mismatch.json

demo-toggle-loop:
	$(PYTHON) -m windows_network_toolkit analytics-summary --fixture fixtures/proxy/localhost-toggle-loop.json --format human

demo-suspicious-proxy:
	$(PYTHON) -m windows_network_toolkit proxy-status --fixture fixtures/proxy/suspicious-remote-proxy.json

demo-report:
	$(PYTHON) -m windows_network_toolkit reviewer-demo --mode mixed --out demo-output/reports

demo-audit-verify:
	$(PYTHON) -m windows_network_toolkit audit verify tests/fixtures/risk_analytics/audit_sample/incidents.jsonl || echo "Sample audit is illustrative — hash chain may not verify"

# Production-shaped stack: Postgres + Redis + API + RQ worker + Prometheus + Grafana
prod-demo-up:
	docker compose up --build -d

prod-demo-down:
	docker compose down

prod-demo-health:
	curl -sf http://127.0.0.1:8000/health
	curl -sf -H "X-Api-Token: dev-trisk-token" -H "X-Api-Role: operator" http://127.0.0.1:8000/v1/incidents

prod-demo-benchmark:
	$(PYTHON) -m windows_network_toolkit fleet-benchmark --scenario mixed_proxy_failures --endpoints 1000 --seed 42 --format markdown --out reports/benchmarks/fleet-1000.md

prod-demo-report:
	curl -sf -H "X-Api-Token: dev-trisk-token" -H "X-Api-Role: auditor_readonly" http://127.0.0.1:8000/v1/reports/executive
