# Case 3: TLS Path Mismatch (MITM Risk Review)

## Symptom

HTTPS via system proxy shows different certificate chain than direct path; security review requested.

## Observation

| Signal | Value | Tier |
|--------|-------|------|
| WinINET proxy | `127.0.0.1:8888` | OBSERVED_ONLY |
| Direct cert issuer | Corp Internal CA | CORRELATED |
| Proxied cert issuer | Charles Proxy CA | CORRELATED |
| Fingerprint mismatch | yes | CORRELATED |

## Hypothesis

TLS path through localhost intercept differs from direct path — supports investigation, **not** confirmed MITM attribution.

## Evidence

- `tls_proof.certificate_mismatch=true`
- `mismatch_fields`: issuer, fingerprint_sha256
- Missing registry writer telemetry

## Proof level

**Supported** for path difference (ordinal ~0.78); **not** definitive MITM or malware proof.

## Policy decision

**DEFER** destructive containment — collect writer proof and approval workflow first.

## Remediation preview

Preview-only guidance: review approved proxy tools; no auto kill/disable without plan.

## Limitations

- Certificate contrast ≠ confirmed MITM
- Does not identify attacker or writer without telemetry
- Policy ALLOW ≠ safety guarantee

## Audit trail

`event_id=evt-case3-tls`, `source=tls-proof`, `evidence_tier=CORRELATED`, `classification=TLS_PATH_MISMATCH`, `policy_decision=DEFER`

## Interview explanation

> "TLS mismatch triggers risk review, not autonomous blocking. We document path contrast, defer strong claims, and require telemetry before containment."

## Demo commands

```powershell
python -m windows_network_toolkit tls-proof --url https://internal.example.com --fixture tests/fixtures/case_studies/case_3_tls_mismatch.json
python -m windows_network_toolkit evidence-report --url https://internal.example.com --fixture tests/fixtures/case_studies/case_3_tls_mismatch.json --format markdown
python -m windows_network_toolkit audit verify .audit/agent-actions.jsonl
```
