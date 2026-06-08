.PHONY: test lint typecheck demo demo-tier1 replay-fixtures install verify-lint verify-format

PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTEST) -q

lint:
	ruff check .

verify-lint:
	ruff check .

verify-format:
	black --check .

typecheck:
	mypy

# Starts API in fixture mode (requires uvicorn; blocks terminal).
demo:
	PLATFORM_FIXTURE_MODE=1 $(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Read-only fixture pipeline (same steps as scripts/demo_tier1.ps1).
demo-tier1:
	$(PYTHON) -m src diagnose --fixture tests/fixtures/features_healthy_signals.json
	$(PYTHON) -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json
	$(PYTHON) -m src proxy-report --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) tools/public_release_audit.py --tracked-only
	$(PYTEST) -q tests/test_policy_safety_contract.py tests/test_api_dry_run_default.py tests/test_replay_determinism.py tests/test_audit_contract.py

replay-fixtures:
	$(PYTHON) -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json
