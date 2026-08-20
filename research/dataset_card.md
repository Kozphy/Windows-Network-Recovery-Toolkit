# Dataset Card

## Dataset purpose

Frozen Windows proxy/reliability evidence for deterministic classifier evaluation, regression testing, and reviewer reproducibility.

## Sources

The current repository contains deterministic fixtures and a real-evidence case pack. Before any quantitative research claim, produce a manifest that identifies exactly which files are included in development, validation, and final evaluation.

## Unit of analysis

One case represents one logically coherent endpoint evidence snapshot or replay scenario. Multiple files derived from the same incident must stay in the same split to avoid leakage.

## Labels

Labels must correspond to reliability/control incident classes used by the deterministic classifier. Malware, compromise, or actor-attribution labels are out of scope.

## Leakage controls

- never split files from the same underlying incident across development and evaluation
- do not tune rules using final evaluation labels
- hash the final fixture manifest before running reportable metrics
- document duplicate or near-duplicate cases

## Representativeness

The fixture collection is a portfolio/research dataset, not a statistically representative sample of all Windows enterprise endpoints. Coverage should be reported by Windows configuration pattern, incident class, evidence tier, and source availability.

## Quality checks

For each case verify:

- stable case ID
- provenance category: synthetic, deterministic fixture, or real-evidence-derived
- expected label and rationale
- required evidence availability
- timestamp consistency where applicable
- no secret, credential, or unnecessary personal data

## Required manifest fields

`case_id`, `split`, `provenance`, `expected_label`, `evidence_tier_expected`, `source_paths`, `sha256`, `notes`.

Until a frozen manifest is generated, quantitative claims should be described as protocol-ready rather than experimentally validated.
