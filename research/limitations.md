# Research Limitations and Non-Claims

This research layer evaluates decision quality within the repository's bounded endpoint-reliability problem. It does not convert the project into a security product or production deployment.

## Current limitations

- Most evaluation evidence is fixture-based and may not reflect enterprise incident prevalence.
- Synthetic fleet scale demonstrates computational behavior, not real operational reliability.
- Ground-truth labels can contain author bias and require independent review for stronger claims.
- Confidence values are ordinal ranking signals, not calibrated probabilities.
- Windows proxy/TLS failure modes are a narrow subset of endpoint reliability incidents.
- Local benchmark latency does not establish Azure, WAN, or global service latency.
- Rule/state-machine methods may encode assumptions that fail on unseen environments.
- Any future human-labelled dataset should document annotator instructions and disagreement.

## Non-claims

Do not claim that this work demonstrates:

- malware, compromise, MITM, EDR, or XDR detection
- universal endpoint-failure diagnosis
- autonomous safe remediation
- production availability or enterprise-scale SLO achievement
- formal audit assurance
- statistically significant superiority unless sample size and method justify it
- Cambridge/Oxford-level research acceptance or peer-reviewed publication

## What a defensible result can establish

A reproducible experiment may establish that, **on a specified versioned evaluation set**, the evidence-tier method changes classification quality, abstention behavior, or remediation-safety metrics relative to defined baselines.

External validity must be argued separately from internal experimental correctness.
