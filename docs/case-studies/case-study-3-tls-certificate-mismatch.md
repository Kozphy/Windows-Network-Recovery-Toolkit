# Case Study 3 — TLS Certificate Path Mismatch

## Business Problem

HTTPS failures or security alerts may indicate TLS interception, corporate proxy misconfiguration, or benign path differences. Teams need **structured contrast** between direct and proxied certificate chains without automatic blocking.

## Technical Symptom

- Browser HTTPS fails or shows certificate warnings
- Direct path vs proxied path return different issuers, roots, or SAN behavior
- Proxy may be enabled or traffic may be redirected locally

## Evidence Collected

| Check | Purpose | Tier |
|-------|---------|------|
| Direct TLS handshake | Baseline certificate chain | Observation |
| Proxied TLS handshake | Contrast path | Observation |
| Issuer / root comparison | Detect mismatch | Proof (if ≥2 indicators) |
| Known corporate proxy allowlist | Reduce false positives | Correlation |

```powershell
python -m windows_network_toolkit tls-proof --url https://example.com --fixture <fixture>
python -m windows_network_toolkit website-risk --url https://example.com --fixture <fixture>
```

## Classification

**Primary:** `POSSIBLE_MITM_RISK` (only when supported by structured contrast — not heuristic alone)

## Proof Level

Requires **multiple independent indicators** per platform policy. Single signal is insufficient for high-confidence security classification.

## Risk Assessment

| Dimension | Rating |
|-----------|--------|
| Inherent risk | High if proof-supported |
| Residual risk | Requires certificate store and network path validation |
| False positive risk | High if based on heuristics only |

## Policy Decision

**Outcome:** Typically `REQUIRE_TYPED_CONFIRMATION` or security escalation — not autonomous block.  
Remediation previews remain non-destructive; no silent cert deletion.

## Remediation Preview

- Document chain differences in governance report
- Escalate to Security / GRC for path validation
- Allowlisted WinINET proxy disable only if reliability root cause confirmed separately

## Limitations

- Heuristic website risk is not EDR-grade
- TLS contrast does not prove malicious intent without organizational context
- Observation ≠ proof; correlation ≠ causation
- Not antivirus or autonomous remediation

## Audit Trail

Store TLS proof envelopes, timestamps, and limitations in JSONL. Hash-chain verification where enabled.

## Interview Explanation

> "For FinTech and cyber risk audiences, TLS path mismatch is the bridge between **operational resilience** and **security governance**. The platform documents what we can contrast technically while explicitly refusing to turn heuristics into automated blocking verdicts."

**Related:** [case-study-3-endpoint-reliability-decision-engine.md](../case-study-3-endpoint-reliability-decision-engine.md) · Fixture: `tests/fixtures/case_studies/case_3_tls_mismatch.json` (when present)
