# 90-Second Interview Pitch

*Read aloud — ~90 seconds at moderate pace.*

---

One project I built is a **Technology Risk & Control Analytics Platform**.

The business problem is familiar: employees report that browsers and business apps are down, but ping and DNS still work. IT support, security, and audit teams often disagree on root cause — and quick-fix scripts change registry settings without evidence or audit trails.

I built a Python and FastAPI platform that treats these incidents as **technology risk decisions**, not one-off fixes. It collects structured evidence from Windows endpoint signals — WinINET and WinHTTP proxy state, localhost listeners, and TLS path contrast — then runs a proof engine that separates **observation from proof** and **correlation from causation**.

On top of that evidence layer, I added a business and control layer: business objectives, assets, threats, control tests, findings, risk ratings, and governance reports. A consultant or IT Risk team can run control tests, see whether detective and preventive controls are working, and export **audit-ready management reporting** — while remediation stays **preview-only by default** with typed confirmation and rollback review.

The golden case is a dead localhost WinINET proxy: classification `DEAD_PROXY_CONFIG`, proof supported, risk rated Medium, remediation gated as preview-only. The platform explicitly documents what it **cannot** prove — it is not antivirus, EDR, or autonomous remediation.

This is relevant to Big 4 and risk advisory work because it translates technical failure modes into **control weaknesses**, **test procedures**, **risk ratings**, and **governance artifacts** — the same language clients use for IT general controls, incident management, and operational resilience.

I'd be happy to walk through a five-minute live demo or discuss how the model extends to FinTech API and TLS incidents.

---

**Demo follow-up:** [big4_demo_flow.md](big4_demo_flow.md)
