# Cyber Risk Consultant Demo

**Audience:** Cyber Risk, IT Risk Advisory, Technology Risk Consultant

**Duration:** ~8 minutes

## Flow

```text
incident → evidence → control failure → policy gate → remediation preview → audit trail → governance report
```

## Steps

1. **Incident observation** — dead WinINET proxy (reliability, not malware verdict)

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

2. **Evidence & proof** — structured proof envelope

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

3. **Control test** — drift + remediation safety

```powershell
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
pytest -q tests/test_control_test_engine.py
```

4. **Policy gate** — preview only

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

5. **Audit trail**

```powershell
python -m windows_network_toolkit audit verify tests/fixtures/analytics/audit_sample/incidents.jsonl
```

6. **Governance report**

```powershell
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown
```

## Talking points

- Classification is not accusation (`UNKNOWN_LOCAL_PROXY`, `POSSIBLE_MITM_RISK`).
- Framework mapping: [framework_mapping.md](framework_mapping.md).
- Not EDR/SIEM/autonomous remediation.
