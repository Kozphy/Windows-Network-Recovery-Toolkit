# Technology Risk & Control Matrix

Maps endpoint reliability failure modes to **business objectives**, **controls**, **test procedures**, and **governance owners**. Use in workshops, internal audit walkthroughs, and Big 4 case interviews.

**Disclaimer:** Informational mapping — not a formal SOC 2 or regulatory attestation.

---

## Control matrix

| Business Objective | Asset | Threat / Failure Mode | Control | Test Procedure | Evidence Produced | Finding | Risk Rating | Remediation Recommendation | Governance Owner |
|------------------|-------|----------------------|---------|----------------|-------------------|---------|-------------|---------------------------|------------------|
| Maintain reliable browser access | Windows endpoint WinINET proxy settings | Dead localhost proxy breaks browser traffic | Proxy configuration monitoring and drift detection | Compare WinINET, WinHTTP, listener state, and direct/proxied path | `proxy-status` JSON, `diagnose --proof` envelope, timeline | `DEAD_PROXY_CONFIG` + `WININET_WINHTTP_MISMATCH` | Medium | Disable proxy only after typed confirmation and rollback review | IT Operations / Endpoint Engineering |
| Ensure authorized configuration changes | Registry proxy settings (HKCU Internet Settings) | Unknown process modifies proxy without approval | Registry writer attribution using Sysmon E13 or equivalent telemetry | Correlate registry changes with process writer telemetry | Writer attribution report, timeline merge | `CORRELATED` or `PROVEN_REGISTRY_WRITER` (tier-dependent) | Medium/High depending on evidence tier | Escalate to Security Operations; do not remediate without validation | Security Operations / IT Risk |
| Protect HTTPS trust path | HTTPS trust path / certificate store | Possible MITM or suspicious root CA | Direct vs proxied TLS certificate contrast | Compare certificate chain, issuer, root CA, and path behavior | TLS proof report (`tls-proof`) | `POSSIBLE_MITM_RISK` if mismatch exists | High if supported by proof | Certificate store review; network path validation; no silent blocking | Security / GRC |
| Prevent unsafe remediation | Endpoint configuration | Over-aggressive scripts cause outage or destroy evidence | Policy-gated dry-run remediation | Verify dry-run default, typed confirmation, no silent kill/reset/disable | Policy decision JSON, audit log, CI safety tests | `PREVIEW_ONLY` or `REQUIRE_TYPED_CONFIRMATION` | Medium | Preview-only by default; apply only with approval and rollback | Platform Engineering / IT Governance |
| Support audit and incident reconstruction | Incident evidence trail | Incomplete or non-replayable evidence | Append-only hash-chained JSONL audit | Verify audit chain and deterministic replay | `audit verify` result, replay output | Audit chain valid / invalid | Medium | Harden log storage; integrate SIEM export (roadmap) | Internal Audit / Risk Advisory |

---

## Evidence tier reference

| Tier | Meaning | Example |
|------|---------|---------|
| Observation | What we read or saw | Registry `ProxyEnable=1` |
| Correlation | Signals align but writer unproven | Listener matches port; no Sysmon E13 |
| Proof | Structured contrast tests passed | `diagnose --proof` → supported |
| Attribution | Registry writer identified | Sysmon E13 process match |
| Final causation | Strong telemetry + impact proof | Requires explicit validation — rarely claimed |

**Rule:** Never collapse tiers in client-facing or audit language.

---

## CLI mapping

| Matrix row | Primary commands |
|------------|------------------|
| Browser access reliability | `proxy-status`, `diagnose --proof`, `risk-assess` |
| Unauthorized proxy change | `proxy-writer-attribution`, `proxy-watch` |
| TLS path mismatch | `tls-proof`, `website-risk` |
| Remediation safety | `proxy-disable --dry-run`, `principles validate` |
| Auditability | `audit verify`, `replay`, `governance-report` |

---

## Related docs

- [big4_interview_positioning.md](big4_interview_positioning.md)
- [governance/control_mapping.md](governance/control_mapping.md)
- [proof-vs-observation.md](proof-vs-observation.md)
