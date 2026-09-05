# Security Governance Crosswalk

This is a portfolio control mapping, not a certification statement or audit opinion.

| Repository capability | NIST CSF 2.0 | CIS Controls v8 | ISO/IEC 27001:2022 theme | MITRE ATT&CK context |
|---|---|---|---|---|
| Asset and software inventory | ID.AM | 1, 2 | asset management | software and endpoint context |
| Evidence integrity and hash chaining | PR.DS / DE.CM | 3, 8 | information protection, logging | supports investigation; not attribution |
| Policy-gated remediation | GV.PO / PR.PS | 4, 16 | change management, secure development | limits abuse of administrative actions |
| Human approval for risky changes | GV.RR / PR.AA | 5, 6 | roles, access control | mitigates unauthorized execution |
| Threat model and abuse cases | ID.RA | 7, 16 | risk assessment, secure development | ATT&CK techniques used as hypotheses |
| Audit and governance reporting | GV.OV / DE.CM | 8 | monitoring, compliance | evidence for detection and review |
| Replay and safety-contract CI | PR.PS / RC.IM | 16, 18 | testing, continual improvement | validates defensive logic |
| Secrets and dependency scanning | PR.PS | 2, 16 | supplier and development security | reduces supply-chain exposure |

## Minimum secure SDLC controls

- Branch protection and reviewed pull requests.
- Pinned or bounded dependencies and automated dependency review.
- Secret scanning and push protection.
- CodeQL or equivalent static analysis.
- SBOM generation for releases.
- Signed release provenance where the build platform supports it.
- Threat-model review for new privileged operations.
- Security test cases for every policy bypass or mutation path.
- Documented vulnerability intake and remediation expectations.

## Evidence governance

- Classify evidence by confidentiality and retention requirement.
- Record evidence source, collection time, tool version, and integrity hash.
- Restrict raw endpoint evidence to roles with a business need.
- Retain derived governance metrics longer than sensitive raw evidence where appropriate.
- Record exceptions with owner, rationale, compensating control, approval, and expiry date.

## ATT&CK use boundary

ATT&CK mappings should describe observable technique hypotheses such as proxy modification, command execution, or persistence-related configuration. They must not be converted into a malware-family or compromise verdict without validated forensic evidence.
