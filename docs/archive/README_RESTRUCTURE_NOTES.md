# README Restructure Notes

## Purpose

The root README now acts as a reviewer landing page rather than a combined landing page, CLI manual, troubleshooting runbook, architecture specification, interview pack, and documentation index.

## Information architecture

The root README answers:

1. What is the platform?
2. What problem does it solve?
3. How does the evidence-to-action flow work?
4. What can a reviewer run in three minutes?
5. What engineering and technology-risk capabilities does it demonstrate?
6. What does it explicitly not claim?
7. Where should each reviewer go for deeper material?

Detailed material remains in existing focused documents:

- Platform / SRE: `docs/faang-platform-review.md`
- Technology risk / audit: `docs/big4-interview-defense.md`
- Power BI / PL-300: `docs/powerbi-interview-story.md`
- Complete CLI: `docs/cli_reference.md`
- Architecture: `docs/architecture.md`
- Onboarding: `docs/ONBOARDING.md`
- Documentation map: `docs/DOCUMENTATION_INDEX.md`

## Scope

This refactor changes documentation only. It does not alter classifiers, policy gates, remediation behavior, audit formats, APIs, tests, or CI safety contracts.
