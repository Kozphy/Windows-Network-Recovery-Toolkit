# Threat model — abuse scenarios (spec format)

**Portfolio prototype** — technology risk evidence and endpoint reliability analytics. Not EDR, not malware detection, not autonomous remediation.

Cross-link: [threat_model.md](threat_model.md) (assets, attacker model, architecture).

Test contracts: `tests/test_policy_safety_contract.py`, `tests/test_proxy_classifier_safety_contract.py`, `tests/test_governance_safety_contracts.py`, `tests/platform_core/governance/test_audit_tamper_detection.py`.

---

| # | Risk | Existing control | Required behavior | Test coverage | Gap / future work |
|---|------|------------------|-------------------|---------------|-------------------|
| 1 | Operator treats classification as malware verdict | Non-claim language in reports; no `MALWARE_*` classes | Classifications are triage labels with `limitations[]` | `tests/test_non_claim_regression.py`, `tests/test_proxy_classifier_safety_contract.py` | UI banners in future dashboard |
| 2 | Autonomous registry repair without confirmation | Dry-run default; `DISABLE_WININET_PROXY` token | No live apply without typed phrase | `tests/test_policy_safety_contract.py`, `tests/windows_network_toolkit/test_safety_contract.py` | Agent-side double-confirm |
| 3 | API caller forces destructive execute | `PLATFORM_SAFE_MODE`, `DEMO_MODE` blocks execute | HTTP 403 or dry-run forced on demo/safe paths | `tests/test_docker_demo_contract.py`, `tests/api/` | Full RBAC on `/platform/execute` |
| 4 | Listener PID misread as registry writer proof | `WRITER_LIMITATION` on owner controls; ADR-004 | Correlation capped without Sysmon E13 | `tests/test_evidence_level_contract.py` | Mandatory telemetry gate for PROVEN tier |
| 5 | Stale fixture replay presented as live proof | Replay recomputes policy; fixture inject labeled | Outputs must state observation vs proof tier | `tests/test_replay_determinism.py`, reviewer-demo stdout | Timestamp freshness checks in fleet ingest |
| 6 | Audit log tampering after incident | Append-only JSONL; hash chain verify | Detect altered rows | `tests/platform_core/governance/test_audit_tamper_detection.py` | External anchor / WORM storage |
| 7 | Governance report read as formal audit opinion | `management information` boundary in templates | No audit opinion wording | `tests/test_governance_safety_contracts.py`, `tests/test_api_demo_contract.py` | Legal review of export templates |
| 8 | Fleet sim output mixed with production data | `fleet-simulate` synthetic endpoint IDs | Clear `limitations[]` on every row | `tests/test_fleet_simulate.py` | Ingest tag `source=synthetic` |
| 9 | Docker demo stack used for live remediation | `DEMO_MODE` forces dry-run; minimal compose | No Postgres required; read-only fixtures | `tests/test_docker_demo_contract.py` | Network policy on demo container |
| 10 | Over-trust in TLS path contrast as MITM proof | Proof module states limitations | No `MITM_CONFIRMED` string | `tests/test_non_claim_regression.py` | Separate MITM module out of scope doc |

---

## Explicitly not in scope

- Antivirus / EDR / XDR replacement
- Autonomous containment or repair
- Guaranteed attribution without Sysmon/Procmon-class telemetry
- Multi-tenant SaaS security hardening in this repository
