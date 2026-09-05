# Evidence-Tiered Endpoint Risk Decisions: A Reproducible Proxy-Failure Benchmark

**Preprint — version 0.1 (September 2026)**

**Author:** Kozphy  
**Repository:** `Kozphy/Windows-Network-Recovery-Toolkit`  
**Artifact version:** Proxy Risk Benchmark v1  
**Evaluation code revision:** `4660a5a76bc2c7724403222434060f363d5f66f7`  
**Dataset SHA-256:** `77edc7334336a16b6614b699940050b0dafbaf62ac09872e52a12aaaaf2af792`

## Abstract

Endpoint troubleshooting systems can produce operationally plausible conclusions while omitting the evidence needed to justify them. This preprint presents an executable evaluation of an evidence-tiered, policy-gated decision system for Windows proxy and network-path failures. The study asks whether deterministic aggregation of connectivity, WinINET and WinHTTP configuration, listener/process attribution, path health, and timeline evidence improves classification quality and decision support compared with three simplified diagnostic baselines. We publish a schema-validated synthetic dataset of 12 cases across development, repository-held-out, and adversarial splits; four baselines; four ablations; machine-generated metrics; raw per-case results; and a digest-bound environment manifest. On this fixture set, the full system reached macro F1 1.000, versus 0.129 for connectivity-only, 0.359 for flat rules, and 0.384 for a health-status baseline. Removing listener evidence, path-health evidence, WinHTTP contrast, or timeline evidence reduced macro F1 to 0.742, 0.455, 0.879, and 0.879, respectively. Deterministic replay produced zero mismatches. These results establish implementation behavior only on the published, repository-authored fixtures. They do not establish enterprise accuracy, mean-time-to-repair improvement, malware detection, or autonomous-remediation safety. The external-validation protocol included with the artifact is therefore a required next phase rather than a completed claim.

## 1. Introduction

Endpoint network failures are often diagnosed from observations that live at different layers. A host may be reachable while a browser fails; WinINET and WinHTTP may disagree; a configured local proxy may have no listener; or a listener may exist but belong to an unexpected process. A diagnostic system that collapses these signals into a single health flag can be fast but epistemically weak. It may also recommend configuration changes before the failure mechanism is adequately supported.

This work evaluates a deterministic alternative. The system aggregates normalized evidence, records explicit limitations, assigns a proof tier, and evaluates policy before proposing action. Remediation remains preview-only in the research benchmark. The central research question is:

> Can deterministic, evidence-tiered endpoint diagnosis improve classification quality, auditability, and decision reproducibility compared with simpler rule-based troubleshooting baselines?

The contribution is an executable research artifact, not a claim of field deployment. Specifically, the artifact provides:

1. a public, versioned failure-scenario dataset;
2. credible simplified baselines and a full-system baseline;
3. machine-generated classification, false-positive, safety, and replay metrics;
4. a component ablation study;
5. strict schemas, digests, and a one-command reproduction path; and
6. an external-user protocol that separates future field evidence from repository-authored evidence.

## 2. System and Evidence Model

Each case contains normalized observations and a predeclared expected outcome. The evaluated evidence families include basic connectivity, WinINET proxy configuration, WinHTTP configuration, local proxy listener and process attribution, direct and proxy-path health, and timeline context. The full system maps these observations to an incident class, proof tier, policy posture, supporting evidence, and explicit limitations.

The decision contract is conservative. A classification can abstain when evidence is insufficient, and an action is considered unsafe when it is proposed despite an expected preview-only or blocked posture. No benchmark path makes a live Windows configuration change.

### 2.1 Failure taxonomy

The case taxonomy covers healthy operation, upstream or general network failure, stale local proxy configuration, missing local listener, suspicious or unexpected listener attribution, WinINET/WinHTTP configuration drift, path-specific failure, and insufficient-evidence states. Taxonomy labels are stored with the fixtures rather than inferred after seeing aggregate results.

### 2.2 Evidence tiers

Proof tiers distinguish direct observation from weaker inference. They are not probabilistic confidence scores. Their purpose is to expose what the system actually observed, what it inferred, and what it could not establish. This distinction supports both operator review and deterministic audit replay.

## 3. Experimental Design

### 3.1 Dataset

Proxy Risk Benchmark v1 contains 12 synthetic and sanitized cases: four development cases, four repository-held-out cases, and four adversarial cases. The directory name `held_out` means that the split is excluded from aggregate rule tuning during the benchmark run. It does **not** mean independent authorship: all current cases were created within the repository project. This limitation is material because implementation knowledge may influence fixture construction.

All cases validate against `experiments/schemas/proxy-risk-case-v1.schema.json`. The loader rejects unknown fields, duplicate identifiers, and mismatches between a case's declared split and its directory. The aggregate dataset digest is recorded above and in the generated manifest.

### 3.2 Compared systems

- **B0 — Connectivity-only:** predicts from basic reachability and represents a common minimal health check.
- **B1 — Flat rules:** maps observations directly to labels without proof-tier aggregation.
- **B2 — Health status:** uses the existing normalized health outcome as a conventional diagnostic summary.
- **B3 — Full platform:** uses deterministic cross-signal aggregation, proof tiers, limitations, and policy posture.

No ML or LLM baseline is reported in v1. This omission is deliberate: the available dataset is too small and repository-authored to support a meaningful trained-model comparison. Future work will add a frozen prompt/model baseline only after expanding the independently labeled evaluation set and recording model, provider, prompt, temperature, and request/response artifacts.

### 3.3 Metrics

The benchmark reports accuracy, macro precision, macro recall, macro F1, macro false-positive rate, per-class precision and recall, a confusion matrix, unsupported-classification rate, abstention rate, policy-match rate, unsafe-action-proposal rate, replay mismatch count, and runtime. Macro metrics are primary because the case taxonomy is multiclass and the fixture count is small. Exact raw predictions are retained to avoid relying on transcribed tables.

Repair time is not measured in v1. Measuring computation time is not a substitute for measuring time-to-diagnosis or time-to-repair with operators. The external-validation protocol defines those human-task metrics for the next phase.

### 3.4 Reproducibility and integrity

The runner executes every case twice and compares decision-relevant outputs. It records the dataset, configuration, and raw-results SHA-256 digests along with the code revision, seed, Python version, and platform. The report builder refuses to summarize raw results when the recorded digest does not match. Machine runtime is measured but excluded from replay-equality checks.

The experiment can be reproduced from the repository root with:

```powershell
python experiments/scripts/run_benchmark.py --config experiments/configs/proxy-risk-v1.json --out experiments/results/v1
python experiments/scripts/build_report.py --results experiments/results/v1 --out benchmarks/v1
```

### 3.5 Ablations

Four same-dataset ablations remove one evidence component at a time:

- **A1:** listener/process attribution;
- **A2:** direct and proxy-path health;
- **A3:** WinHTTP contrast; and
- **A4:** timeline evidence.

The comparison asks whether each component changes classification performance rather than assuming that additional evidence is useful by construction.

## 4. Results

### 4.1 Baseline comparison

| System | Accuracy | Macro precision | Macro recall | Macro F1 | Macro FPR | Unsupported | Unsafe proposals |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 Connectivity | 0.250 | 0.089 | 0.273 | 0.129 | 0.074 | 0.417 | 0.000 |
| B1 Flat rules | 0.500 | 0.333 | 0.455 | 0.359 | 0.050 | 0.917 | 0.167 |
| B2 Health status | 0.417 | 0.375 | 0.455 | 0.384 | 0.058 | 0.333 | 0.000 |
| B3 Full platform | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |

These values apply only to the 12 published fixtures. B1's unsafe-proposal rate of 0.167 corresponds to two of 12 cases. The full platform produced zero replay mismatches across the double run.

### 4.2 Ablation results

| Ablation | Macro F1 | Change from B3 |
|---|---:|---:|
| A1 No listener/process evidence | 0.742 | -0.258 |
| A2 No path-health evidence | 0.455 | -0.545 |
| A3 No WinHTTP contrast | 0.879 | -0.121 |
| A4 No timeline evidence | 0.879 | -0.121 |

Every evaluated ablation reduced macro F1 on the combined fixture set. The largest observed reduction followed removal of path-health evidence. Given the small and constructed sample, these differences are descriptive; no population-level statistical inference is claimed.

### 4.3 Failure analysis

The connectivity-only baseline confuses application-path and proxy failures with general reachability outcomes. The health-status baseline loses distinctions needed for root-cause labels. Flat rules recover some cases but omit supporting evidence in most predictions and can propose action without the expected policy posture. Detailed case-level errors, per-class metrics, and the confusion matrix are published under `benchmarks/v1/`.

## 5. Discussion

The experiment supports a narrow conclusion: within the encoded proxy-risk scenarios, cross-signal evidence changes decisions and the full implementation conforms to the fixture oracle. The ablations also demonstrate that the extra evidence fields are behaviorally active rather than documentation-only inputs.

The perfect B3 result should not be interpreted as generalization. The classifier and dataset share a repository and may share design assumptions. The correct reading is closer to executable specification conformance than to an estimate of field accuracy. Independent cases are needed to test whether the taxonomy and rules transfer to unfamiliar environments.

The artifact's strongest current evidence concerns reproducibility. Stable fixtures, strict validation, frozen code and dataset identifiers, deterministic replay, and raw-result digests make it possible to audit how a reported number was produced. This is valuable even before external validity is established, because it prevents a portfolio demonstration from being presented as field evidence.

## 6. Threats to Validity

**Internal validity.** Repository authors created both the system and the fixtures. Expected labels may therefore encode implementation assumptions. Split separation reduces accidental tuning but does not create independent authorship.

**External validity.** Twelve proxy-centric cases cannot represent Windows endpoint failures broadly, heterogeneous enterprise policy, managed browsers, VPN products, EDR interference, or organizational workflows.

**Construct validity.** Classification correctness is not equivalent to operator usefulness. Likewise, runtime in milliseconds is not time-to-repair. Human task studies are required for comprehension, action quality, and repair-time claims.

**Baseline validity.** B0–B2 are deterministic simplified tools. No traditional vendor diagnostic suite, ML model, or LLM was executed. Comparisons must therefore remain scoped to the implemented baselines.

**Safety validity.** Zero unsafe proposals on fixtures does not prove that autonomous remediation is safe. The benchmark evaluates decision outputs in preview-only mode and never exercises live recovery actions.

## 7. External Validation Plan

The repository includes `validation/external-user-study-v1.md` and a machine-readable response template. The planned study uses independently supplied, sanitized scenarios and a within-participant comparison between the participant's normal workflow and the evidence-tiered report. Primary outcomes are task-level diagnosis correctness, unsupported conclusions, unsafe change proposals, time-to-diagnosis, and time-to-safe-next-action. Secondary outcomes include decision confidence and evidence-traceability ratings.

External validation will be reported only after the minimum study threshold is met and provenance is auditable. Until then, the status is **protocol ready; validation not yet completed**.

## 8. Conclusion

This work turns endpoint-risk claims into a runnable benchmark with explicit evidence boundaries. On a small synthetic proxy-failure dataset, the evidence-tiered system outperformed three simplified deterministic baselines, all four evidence ablations reduced macro F1, and replay was deterministic. The result is a reproducible engineering evaluation and a basis for independent testing—not proof of enterprise effectiveness. The next milestone is an externally authored dataset and operator study measuring diagnosis quality and time-to-safe-action.

## Artifact Availability

The dataset, schema, configuration, raw results, generated tables, failure analysis, environment record, and external-validation protocol are versioned in the public repository. The benchmark's `manifest.json` is the authoritative link between code, data, configuration, and raw outputs.

