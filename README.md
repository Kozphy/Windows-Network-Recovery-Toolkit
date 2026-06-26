# Technology Risk & Control Analytics Platform

Navigation hub — technical depth lives in [`docs/`](docs/). Full index: [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md).

---

## What is it

Evidence-backed Windows endpoint reliability and home/SOHO LAN analytics — explainable classifications, control tests, policy-gated remediation previews, hash-chained audit trails, and governance exports.

Production-**shaped** portfolio prototype — not enterprise-certified software. Not EDR, SIEM, malware detection, spyware detection, autonomous repair, or formal audit opinion.

→ [docs/START_HERE.md](docs/START_HERE.md) · [docs/evidence-model.md](docs/evidence-model.md) · [docs/lan-privacy-monitor.md](docs/lan-privacy-monitor.md) · [docs/safety-model.md](docs/safety-model.md)

---

## Why

Structured triage, control testing, and governance exports for IT ops, technology risk / audit, SRE, and analytics teams.

→ [docs/portfolio-positioning.md](docs/portfolio-positioning.md)

---

## Architecture

Evidence → classification → proof / controls → policy → preview → audit → report → replay.

→ [docs/architecture.md](docs/architecture.md) · [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)

---

## Key Features

Deterministic read-only evidence, proof-tier classification with `limitations[]`, control tests, policy gates (preview-only by default), and replayable audit exports.

→ [docs/evidence-model.md](docs/evidence-model.md) · [docs/proof-tiers.md](docs/proof-tiers.md) · [docs/control-matrix.md](docs/control-matrix.md) · [docs/policy-gates.md](docs/policy-gates.md) · [docs/limitations.md](docs/limitations.md)

---

## Demo

Fixture-safe golden replay (~3 min): `make demo`

→ [docs/demo_5_min.md](docs/demo_5_min.md) · [docs/demo-commands-reference.md](docs/demo-commands-reference.md) · [docs/interview-demo-3min.md](docs/interview-demo-3min.md) · [Reviewer Docker Demo](docs/docker-demo.md) (`docker-compose.demo.yml`)

---

## Quick Start

Clone, install, set `PYTHONPATH`, run `make demo` and `pytest -q`.

→ [docs/quick-start.md](docs/quick-start.md) · [docs/START_HERE.md](docs/START_HERE.md) · [docs/cli_reference.md](docs/cli_reference.md)

---

## Documentation

| Topic | Start here |
|-------|------------|
| **Full index** | [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md) |
| Evidence & classification | [docs/evidence-model.md](docs/evidence-model.md) · [docs/classification-taxonomy.md](docs/classification-taxonomy.md) |
| Controls & audit | [docs/control-matrix.md](docs/control-matrix.md) · [docs/lan-control-matrix.md](docs/lan-control-matrix.md) |
| Incidents | [docs/incident-walkthrough-dead-proxy.md](docs/incident-walkthrough-dead-proxy.md) · [docs/dead-proxy-guardian.md](docs/dead-proxy-guardian.md) |
| Analytics / Power BI | [docs/analytics-powerbi-quickstart.md](docs/analytics-powerbi-quickstart.md) |
| Portfolio / interviews | [docs/portfolio-positioning.md](docs/portfolio-positioning.md) · [docs/big4-interview-defense.md](docs/big4-interview-defense.md) |
| Production depth | [docs/production-readiness-gap.md](docs/production-readiness-gap.md) · [docs/threat-model.md](docs/threat-model.md) |

---

## License

MIT — see [LICENSE](LICENSE).
