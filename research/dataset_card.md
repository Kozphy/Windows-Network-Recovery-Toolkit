# Dataset Card — Windows Technology Risk Telemetry

> Status: template. Complete this card before publishing benchmark claims.

## Dataset identity

- Name:
- Version:
- Collection period:
- Environments represented:
- Number of devices:
- Number of observations:
- Positive/negative class counts:

## Provenance

Describe exactly how telemetry/control evidence was collected. Separate real operational evidence, controlled fault injection and synthetic/demo records.

## Unit of observation

Define what one row represents (for example, one device observation at a specific timestamp).

## Feature contract

Document each feature, unit, valid range, missing-value behavior and derivation. Current prototype features include proxy mismatch, DNS failure rate, TLS error count, adapter reset count, WinHTTP drift and network profile.

## Target / labeling

- Target: `failure_label`
- Positive-class definition:
- Negative-class definition:
- Label observation window:
- Label adjudication process:
- Ambiguous-label handling:

## Splitting policy

Prefer chronological splitting when timestamps are available. Record train, validation and test time boundaries and ensure observations from the future cannot influence training-time feature derivation.

## Leakage review

Document possible target leakage, duplicate-device leakage, post-outcome features and preprocessing fitted outside the training partition.

## Quality checks

- Schema validation
- Missingness
- Duplicate observations
- Class balance
- Outliers
- Impossible values
- Timestamp ordering
- Device/environment concentration

## Privacy and security

Do not commit credentials, secrets, personal identifiers or sensitive production telemetry. Define anonymization/pseudonymization and retention rules before ingesting real organizational data.

## Known limitations

List sampling bias, label noise, environment coverage gaps and threats to external validity.

## Permitted claims

Demo/synthetic data may demonstrate that the software runs. Research-performance claims require this card to be completed and the corresponding immutable dataset/config version to be recorded.