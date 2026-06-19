# Test Strategy — Portfolio & Reviewer Trust

How this repository stays **deterministic**, **offline-safe**, and **audit-defensible**.

---

## 1. Unit tests

| Area | Location | Purpose |
|------|----------|---------|
| Proxy parser / loopback | `tests/test_proxy_guard_parser.py` | Host/port parsing, IPv6 loopback |
| Proxy state machine | `tests/test_proxy_state_transitions.py` | Fixture-driven transitions |
| Safety contracts | `tests/test_proxy_classifier_safety_contract.py` | No remote proxy on empty after; no malware language |
| Policy gates | `tests/test_policy_safety_contract.py` | No silent mutation/kill/firewall |
| Audit hash chain | `tests/platform_core/governance/test_audit_tamper_detection.py` | Tamper detection |
| Power BI schema | `tests/test_powerbi_star_export.py` | Stable CSV export |

---

## 2. Fixture replay tests

- **Input:** JSON/JSONL under `tests/fixtures/proxy_transitions/`  
- **Engine:** `proxy_replay.py` + `proxy_state_machine.py`  
- **Assertions:** `transition_class`, `primary_classification`, `safety_violations == []`  
- **Invariant:** `test_after_proxy_server_none_is_never_remote_proxy_configured`  

```powershell
python -m windows_network_toolkit proxy-replay --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
pytest -q tests/test_proxy_state_transitions.py
```

---

## 3. Safety contract tests (CI must fail if violated)

| Contract | Test anchor |
|----------|-------------|
| Registry mutation requires typed confirmation | `tests/test_policy_safety_contract.py` |
| Dry-run default on remediation | `tests/test_api_dry_run_default.py` |
| No malware verdict without limitations | `tests/test_cs1_principle_compliance.py` |
| Empty after ProxyServer ≠ remote proxy | `tests/test_proxy_state_transitions.py` |
| Listener ≠ registry writer proof | `tests/test_proxy_classifier_safety_contract.py` |

---

## 4. Full-state vs single-field classification

`tests/test_proxy_state_transitions.py::test_classification_uses_full_state_not_proxy_enable_alone` proves that **ProxyEnable-only diff** would mislead, but full before/after state yields correct `PROXY_DISABLED_AND_SERVER_REMOVED`.

---

## 5. Audit tamper detection

- `verify_chain()` on append-only records  
- Modified `payload` or `classification` breaks chain  
- Tests: `tests/test_governance_safety_contracts.py`, `tests/platform_core/governance/test_hash_chained_audit.py`  

**Proves:** post-write integrity · **Does not prove:** original observations were true  

---

## 6. Running the suite

```powershell
pytest -q                                    # full suite
pytest -q tests/test_proxy_state_transitions.py tests/test_proxy_classifier_safety_contract.py
python tools/public_release_audit.py --tracked-only
```

---

## Related

- [replay-demo.md](replay-demo.md)
- [test_strategy.md](test_strategy.md) (platform-wide matrix)
- [anti-code-paste-defense.md](anti-code-paste-defense.md)
