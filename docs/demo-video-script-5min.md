# 5-Minute Demo Video Script

## 0:00 — Problem (30s)

**Say:** "Corporate laptops often fail in a confusing way — ping works, DNS works, but browsers break. Fix scripts mutate registry without evidence or audit. This platform is decision infrastructure, not an autonomous repair bot."

**Show:** Browser proxy error screenshot placeholder (`docs/screenshots/01-browser-proxy-error.png`).

---

## 0:30 — Proxy drift case (60s)

**Say:** "Case 1: dead WinINET localhost proxy. We observe registry settings, classify `DEAD_PROXY_CONFIG`, and separate observation from proof."

```powershell
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

**Show:** JSON classification + limitations array.

---

## 1:30 — Evidence proof (60s)

**Say:** "Structured proof attempts support the hypothesis — but limitations explicitly say we do not prove malware or MITM."

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

**Highlight:** `proof_attempts`, `conclusion.status=supported`, `limitations[]`.

---

## 2:30 — Policy-gated remediation preview (45s)

**Say:** "Remediation is preview-only by default. Typed confirmation required for any live registry change."

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

**Highlight:** `requires_confirmation`, `confirmation_token`, `no_changes_made=true`.

---

## 3:15 — Fleet simulation (60s)

**Say:** "At fleet scale we aggregate synthetic endpoints — classifications, tiers, policy decisions — without live probes."

```powershell
python -m windows_network_toolkit fleet-simulate --fixture tests/fixtures/fleet/fleet_100_endpoints.jsonl --format json
python -m windows_network_toolkit fleet-simulate --fixture tests/fixtures/fleet/fleet_100_endpoints.jsonl --format markdown
```

**Highlight:** 100 endpoints, classification breakdown, risk buckets.

---

## 4:15 — Dashboard / audit report (45s)

**Say:** "The FastAPI dashboard loads fixture-backed fleet summary, case studies, audit chain status, and replay digest."

```powershell
uvicorn backend.main:app --reload
# Open http://127.0.0.1:8000/dashboard/
curl http://127.0.0.1:8000/platform/fleet/summary?fixture=tests/fixtures/fleet/fleet_100_endpoints.jsonl
curl http://127.0.0.1:8000/platform/demo/case-studies
```

**Show:** Dashboard fleet panel + audit chain ok=true.

---

## 5:00 — Interview positioning (30s)

**Say:** "This is an Endpoint Network Evidence and Risk Platform — IT risk governance, audit-ready incident review, policy-gated remediation preview. It complements EDR and SIEM; it is not antivirus, not autonomous security, not a malware remover."

**Close with principles:**

- Observation ≠ Proof  
- Correlation ≠ Causation  
- Confidence ≠ Certainty  
- Policy Permission ≠ Safety Guarantee  
