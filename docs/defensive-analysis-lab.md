# Defensive Analysis Lab

This lab extends the portfolio toward safe malware-analysis and detection-engineering literacy. It is not an exploit framework, malware launcher, or compromise-verdict engine.

## Allowed workflows

- Calculate SHA-256 and file-size metadata.
- Inspect file type, signer information, PE headers, imports, and embedded strings without execution.
- Ingest reports from an isolated sandbox operated outside this repository.
- Validate YARA rules against benign fixtures and known-safe test samples.
- Validate Sigma rules against synthetic Windows event logs.
- Map observations to ATT&CK techniques as analyst hypotheses.
- Produce a triage report with evidence, confidence, limitations, and escalation guidance.

## Prohibited workflows

- Executing untrusted binaries on the host.
- Developing payloads, persistence, credential theft, evasion, or destructive behavior.
- Automated quarantine or deletion without human authorization.
- Claiming a malware family from weak indicators.
- Uploading confidential samples to third-party services without authorization.

## Suggested report schema

```json
{
  "sample_id": "sha256:...",
  "collection_context": "approved lab fixture",
  "static_observations": [],
  "sandbox_observations": [],
  "candidate_attack_techniques": [],
  "detection_candidates": [],
  "confidence": "low|medium|high",
  "limitations": [],
  "recommended_action": "review|escalate|close"
}
```

## Portfolio exercises

1. Detect a benign PowerShell test event using a Sigma rule.
2. Identify unsigned-versus-signed fixture differences.
3. Compare hashes and import tables across two harmless PE fixtures.
4. Ingest a public sandbox JSON fixture and produce an evidence-based ATT&CK mapping.
5. Measure YARA false positives against a benign corpus.

These exercises show defensive reasoning and detection quality while avoiding unsafe malware execution.
