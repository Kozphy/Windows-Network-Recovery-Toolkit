# Policy model

Canonical decisions (`platform_core/policy_model.py`):

| Decision | Execute | Preview | When |
|----------|---------|---------|------|
| `ALLOW_OBSERVE` | No | No | Healthy baseline or known dev tooling |
| `PREVIEW_ONLY` | No | Yes | Default for partial evidence |
| `REQUIRE_TYPED_CONFIRMATION` | No | Yes | Writer proof or external proxy |
| `BLOCK_DESTRUCTIVE` | No | No | kill/firewall/adapter/shell tokens |
| `BLOCK_LOW_CONFIDENCE` | No | No | Ordinal confidence &lt; 0.4 |
| `CORRELATION_ONLY_ALERT` | No | Yes | Correlation without writer proof |

## Safety invariants

- No silent process kill, firewall reset, or adapter disable
- No registry mutation without typed confirmation
- API `POST /platform/remediation/execute` defaults to `dry_run=true`
- Policy ALLOW/PREVIEW is **not** a safety guarantee

## Policy-as-code

YAML profiles: `config/policies/default.yaml`, `strict_enterprise.yaml`, `developer_workstation.yaml`

```powershell
python -m src policy-validate config/policies/default.yaml
python -m src proxy-policy --fixture tests/fixtures/proxy_incidents/cursor_known_proxy.json --policy config/policies/default.yaml --format json
```

Tests: `tests/test_policy_safety_contract.py`, `tests/test_safety_contract_extensions.py`, `tests/test_api_dry_run_default.py`
