# Test-to-control matrix

Maps CTRL-001–010 from [control-matrix.md](../control-matrix.md) to pytest anchors.

| Control | Test anchor | Fixture examples |
|---------|-------------|------------------|
| CTRL-001 | `tests/platform_core/classification/test_classification_matrix.py` | `fixtures/dead_proxy_config/` |
| CTRL-002 | `tests/test_proxy_state_transitions.py` | `fixtures/wininet_winhttp_mismatch/` |
| CTRL-003 | `tests/windows_network_toolkit/test_proxy_health.py` | `dead_proxy_59081.json` |
| CTRL-004 | `tests/platform_core/attribution/test_listener_classification.py` | `unknown_localhost_proxy.json` |
| CTRL-005 | `tests/test_proxy_state_transitions.py` | `fixtures/pac_configured/` |
| CTRL-006 | `tests/test_proxy_classifier_safety_contract.py` | portfolio evidence fixtures |
| CTRL-007 | `tests/windows_network_toolkit/test_proxy_state_machine.py` | `fixtures/reverter_suspected/` |
| CTRL-008 | `tests/platform_core/proof/test_proof_engine.py` | `fixtures/tls_path_mismatch/` |
| CTRL-009 | `tests/test_policy_safety_contract.py` | policy YAML + CLI dry-run |
| CTRL-010 | `tests/platform_core/governance/test_hash_chained_audit.py` | `audit_sample_chained/` |

Evaluation matrix: `tests/evaluation/test_scenario_matrix_15.py` · `tests/fixtures/evaluation/scenarios_15.json`
