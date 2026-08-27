# Threats to Validity

## Internal
- Fixture telemetry may overfit rule logic written against the same fixtures.
- Dry-run verification injects baseline for preview — must not be mistaken for live recovery proof.

## External
- Results do not generalize to enterprise fleets, SOC tooling, or real adversaries.
- Windows live race conditions / timing are not represented in deterministic fixtures.

## Construct
- "Detection" here means purple rule fire on normalized fixture events — not EDR alert fidelity.
- MITRE mappings are optional metadata and may be approximate; empty mapping preferred over theatre.

## Conclusion
Treat purple metrics as **control-lab evidence**, not production security guarantees.
