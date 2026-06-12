# Three-minute demo script

Deterministic, **no Administrator** required. Works on any OS via fixtures; live probes need Windows.

**Prerequisites**

```powershell
cd Windows-Network-Recovery-Toolkit
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

---

## 0:15 — Positioning

> This is endpoint **reliability infrastructure**, not a repair script. We observe proxy state, classify risk, attempt structured proof, gate remediation behind policy, and append audit events. Primary CLI is JSON-first: `python -m windows_network_toolkit`.

---

## 0:45 — Golden case: dead proxy 59081

**Say:** "Ping works, browser fails — classic WinINET dead localhost proxy."

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Point out in JSON:**

- `classification_result.primary_classification`: `DEAD_PROXY_CONFIG`
- `secondary_signals`: includes `WININET_WINHTTP_MISMATCH`
- `confidence`: ~0.92
- `limitations[]`: no malware/MITM claims

---

## 1:30 — Structured proof

**Say:** "Observation is not proof. Here is what we tested."

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Highlight:**

- `proof_attempts[]` with pass/fail status
- `conclusion.status`: `supported`
- `limitations[]` always present

---

## 2:00 — Safe remediation preview

**Say:** "Dry-run is default. Apply requires a typed token."

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

**Optional on Windows with broken proxy:**

```powershell
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

Audit writes to `.audit/proxy-disable.jsonl`.

---

## 2:30 — Incident report

```powershell
python -m windows_network_toolkit proxy-report --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Sections:** executive summary, classification, proof status, remediation status, limitations.

---

## 2:50 — Close

> Legacy `python -m src` still works but prints a deprecation notice. All new integrations should use the WNT JSON CLI. Full case study: docs/case-studies/dead-localhost-proxy.md

---

## Backup commands

```powershell
python -m windows_network_toolkit proxy-owner --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit proxy-timeline --audit-only
pytest -q tests/platform_core/classification tests/windows_network_toolkit
```
