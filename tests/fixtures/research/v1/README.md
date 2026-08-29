# Synthetic research fixtures v1

This frozen dataset contains deterministic, fictional endpoint observations. It contains no
collected host data, user identifiers, or production telemetry.

- `development/` is available while implementing and debugging adapters.
- `held_out/` is evaluated separately and must not be used to tune rules after v1 is frozen.
- `adversarial/` contains incomplete, contradictory, or unusual-but-valid configurations.

Every case uses `research_case.v1` and separates observed `signals` from predeclared `expected`
outcomes. The manifest at `experiments/manifest.json` records the canonical content digest and
file inventory. Changing a case requires a new dataset version or an explicit manifest update.

The split names are an experimental protocol, not proof of external validity. All cases were
authored in this repository and remain synthetic.
