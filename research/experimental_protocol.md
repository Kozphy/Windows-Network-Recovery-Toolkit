# Experimental Protocol

## 1. Scope

Evaluate deterministic classification of Windows proxy-state drift using frozen fixtures and replayable evidence. This protocol does not evaluate malware detection, enterprise production readiness, or autonomous remediation.

## 2. Pre-registration fields

Before reporting results, record:

- git commit SHA
- Python version and OS
- fixture manifest hash
- configuration hash
- random seed (where sampling/bootstrap is used)
- class mapping
- primary metric
- baseline definitions
- exclusions, if any

Changing any of these after seeing evaluation results requires a new protocol version.

## 3. Data split

Use three non-overlapping logical sets when sufficient fixtures exist:

1. development — implementation/debugging only
2. validation — threshold and rule selection
3. evaluation — final reporting only

If current fixtures are too small for a credible split, report that limitation explicitly and use leave-one-case-out or bootstrap analysis rather than implying generalization.

## 4. Baselines

Run all baselines in `baselines.md` against the same frozen evaluation inputs. No baseline may receive less information than declared in its definition.

## 5. Repetitions

- deterministic classification: 10 repeated runs
- bootstrap uncertainty: 10,000 resamples with a fixed seed
- performance timing: minimum 30 runs after warm-up when timing is reported

## 6. Primary endpoint

Macro-F1 across pre-declared incident classes. Secondary metrics include per-class precision/recall, false-positive rate, explainability completeness, and deterministic replay rate.

## 7. Statistical reporting

Report point estimates and 95% bootstrap confidence intervals. Report absolute differences against baselines. Do not use a confidence interval as proof of practical significance; include effect size and failure cases.

## 8. Ablation

Remove one evidence family at a time while holding all other conditions fixed. Ablations are diagnostic, not a license to tune against the evaluation set.

## 9. Error review

Every false positive, false negative, and low-proof-tier case must be assigned an error category from `error_analysis.md`.

## 10. Reproducibility gate

A result is portfolio-reportable only if another run from the recorded commit and fixture manifest reproduces normalized outputs and metrics within declared tolerances.
