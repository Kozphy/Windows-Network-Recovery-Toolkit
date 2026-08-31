# Purple Team Threat Model (of the platform itself)

| Threat | Control | Residual risk |
| --- | --- | --- |
| Malicious scenario definition | Schema rejects missing cleanup/remote/prod; review scenarios in VCS | Malicious but schema-valid fixtures |
| Privilege abuse | Dry-run default; typed auth; no CI live mutation | Local operator with admin rights |
| Evidence tampering | Chained hashes + bundle hash | Whole-file deletion; tip not WORM |
| Unsafe remediation | Fixture-only remediate in purple runner; live remediation stays in existing gates | Confusion if operators ignore dry-run |
| Collector spoofing | Provenance fields + fixture trust boundary | Fixture author can invent events |
| False / stale telemetry | Confidence + limitations[]; timing failure category | Lab timing ≠ production |
| Replay | Run IDs + timestamps in bundles | Replay of bundles as if live |
| Approval bypass | `approve()` separates recommendation/execution | Bugs in caller wiring |
| Configuration poisoning | Scenario files code-reviewed | Compromised repo |

Trust assumption: verifier trusts the repository and the machine that produced the first tip.
