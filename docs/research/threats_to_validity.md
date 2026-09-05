# Threats to Validity — Diagnostic Research Track

> Complements purple-lab threats in [`../../research/threats_to_validity.md`](../../research/threats_to_validity.md).
> Mandatory for any preprint-facing claims about diagnostic effectiveness.

---

## Construct validity

**Does the benchmark represent endpoint failure diagnosis?**

- Cases use **synthetic or fixture-derived** evidence with author-assigned `expected_incident_class`.
- Labels are reliability triage classes (e.g. `DEAD_PROXY_CONFIG`), not malware or SOC alert fidelity.
- Remediation “success” in the default harness is **posture match / preview correctness**, not measured live repair.
- Taxonomy IDs (`F_*`) and incident classes must be mapped explicitly; mismatch weakens construct alignment.

**Mitigation:** provenance fields; limitations[]; separate development vs held_out; refuse MTTR claims without field instrumentation.

---

## Internal validity

**Could implementation differences unfairly favor the proposed system?**

- Proposed B3 and many fixtures share authorship → risk of **fixture overfitting**.
- Ablations that remove signals the labels depend on will look artificially strong for FULL.
- Baselines may be under-tuned relative to B3 (or vice versa).

**Mitigation:** held-out split; document baseline intent (credible simplified alternatives, not strawmen); freeze manifests; record git SHA.

---

## External validity

**Will synthetic scenarios generalize to enterprise endpoints?**

- No claim of coverage for GPO diversity, VPN/captive portals, multi-user sessions, or vendor EDR interactions.
- Linux CI does not execute live WinINET/WinHTTP collection.
- Purple Team and diagnostic tracks answer different questions; do not conflate metrics.

**Mitigation:** state scope in README and paper; optional future consented field study as a separate experiment ID.

---

## Statistical conclusion validity

**Are sample sizes and tests appropriate?**

- Dataset v1 has on the order of **tens** of cases; bootstrap CIs will be wide.
- Percentile bootstrap assumes exchangeable cases; related fixtures may violate IID.
- Do **not** auto-claim “statistical significance.”
- McNemar / permutation (when added) require paired predictions and documented assumptions.

**Mitigation:** always report n, CI method, seed; prefer estimation + uncertainty over p-hacking.

---

## Dataset bias

- Proxy/dead-localhost families are overrepresented relative to DNS/TLS/policy classes.
- Ambiguous and incomplete-evidence cases exist but may be too few for stable per-class F1.
- Severity tags are coarse.

**Mitigation:** composition tables; per-class metrics with support counts; generator roadmap for balanced coverage (without fabricating live data).

---

## LLM baseline validity (when enabled)

Results may depend on model ID, prompt version, temperature, provider, and release date.

**Mitigation:** stub mode default; cache structured responses; record model/prompt metadata; never require network for CI.

---

## Conclusion posture

Treat current outputs as **reproducible control-lab / fixture evidence** for engineering and research *methods*, not as production security guarantees or peer-reviewed effect sizes until the full comparison stack and disclosure checklist are complete.
