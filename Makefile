.PHONY: test lint typecheck demo replay-fixtures install

PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTEST) -q

lint:
	ruff check platform_core backend evidence failure_system telemetry src tests

typecheck:
	mypy

demo:
	PLATFORM_FIXTURE_MODE=1 $(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

replay-fixtures:
	$(PYTHON) -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
	$(PYTHON) -m src proxy-policy --fixture tests/fixtures/proxy_incidents/suspicious_powershell_temp_proxy.json --format json
