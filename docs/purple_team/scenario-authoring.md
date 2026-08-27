# Scenario Authoring

1. Create fixture under `tests/fixtures/purple_team/`.
2. Create YAML under `scenarios/` with **all** required fields including `cleanup.required: true` and non-empty `cleanup.steps`.
3. Map `expected_detection` to an existing rule or add a rule + tests.
4. Include a benign counterpart when adding a suspicious scenario.
5. Validate: `python -m src.purple_team validate <id>`

Forbidden: remote/production targets, missing rollback, live MITM, credential theft, persistence.
