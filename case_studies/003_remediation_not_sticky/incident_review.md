# Incident review (source notes)

## Impact

- Remediation did not persist — user remains affected
- Repeat blind execute blocked by policy

## Limitations

- Stickiness metric does not identify which process reverted settings
- Requires causation / Sysmon pass for writer proof

## Follow-up actions

- Run final causation bundle
- Apply strict policy if unknown writer
- Document reverter in incident timeline
