# LinkedIn Post — Technology Risk & Control Analytics Platform

*Copy, personalize, and post with repo link or demo video.*

---

I built a **Technology Risk & Control Analytics Platform** to explore how technical incidents can be translated into audit-ready risk and control workflows.

The starting problem is common: browsers and business apps fail while ping and DNS still work. Teams often blame "the network," run aggressive fix scripts, and end up with **unaudited registry changes** and **false security conclusions**.

I approached this as **technology risk infrastructure**, not another troubleshooting script.

The platform collects structured endpoint evidence (WinINET/WinHTTP proxy state, localhost listeners, TLS path contrast), runs a proof engine that separates **observation from proof**, and maps incidents to a consulting frame:

**Business Objective → Asset → Threat → Control → Testing → Finding → Risk Rating → Remediation → Governance**

Key design choices:

- **Dry-run remediation by default** — preview-only unless policy, typed confirmation, rollback, and audit requirements are met
- **Evidence tiers** — observation, correlation, proof, and attribution are never collapsed in reports
- **Control testing CLI** — PASS/FAIL results against detective and preventive controls
- **Audit-ready outputs** — hash-chained JSONL, deterministic replay, management markdown reports
- **Explicit limitations** — does not claim malware detection, EDR replacement, or autonomous remediation

Golden case: dead WinINET proxy `127.0.0.1:59081` — proof-supported `DEAD_PROXY_CONFIG`, Medium risk rating, governance decision `PREVIEW_ONLY`.

Stack: Python 3.11+, FastAPI, Pydantic, pytest (1000+ tests), GitHub Actions CI, Prometheus metrics, optional Next.js dashboard.

This is relevant to **IT Risk**, **Internal Audit**, **technology consulting**, and **FinTech operational resilience** — the same governance pattern applies to API outages, TLS issues, and configuration drift at scale.

Repo includes interview materials: control matrix, 90-second pitch, 5-minute demo script, STAR case study, and resume bullets.

Feedback from IT Risk, GRC, SRE, Security, and FinTech professionals is welcome.

---

**Hashtags (optional):** `#TechnologyRisk` `#ITAudit` `#OperationalResilience` `#Python` `#Governance` `#Consulting` `#FinTech`

**Links to include:**

- GitHub repo
- [docs/README_BIG4_PORTFOLIO.md](README_BIG4_PORTFOLIO.md) path in repo
