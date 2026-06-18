# Control Test Engine

**Module:** `src/platform_core/controls/control_test.py`

Formal control tests for portfolio and audit-backed governance reports.

## Results

| Result | Meaning |
|--------|---------|
| `PASS` | Control objective met for available evidence |
| `FAIL` | Control objective not met |
| `EXCEPTION` | Human-approved exception (fixture-driven demo) |
| `INSUFFICIENT_EVIDENCE` | Test not applicable or data missing |

## Catalog (examples)

| control_id | Objective |
|------------|-----------|
| CT-AUDIT-001 | Proxy changes require audit evidence |
| CT-REG-002 | Registry mutation requires typed confirmation |
| CT-REM-003 | Remediation defaults to dry-run |
| CT-EVID-004 | Low evidence tier must not unlock destructive action |
| CT-CLASS-005 | Unknown local proxy ≠ malware proof |
| CT-TLS-006 | TLS mismatch reported with limitations |

## Usage

```python
from src.platform_core.controls import run_control_test_suite

run_control_test_suite(fixture=case_json)
run_control_test_suite(audit_records=rows)
```

```powershell
pytest -q tests/test_control_test_engine.py
```

Legacy fixture tests remain in `src/platform_core/risk/control_test.py` for `control-test` CLI.
