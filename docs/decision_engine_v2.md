# Decision engine v2 (live hypotheses)

## Inputs

`LiveNetworkSnapshot` merges:

- Existing `FeatureVector` probes (`src/diagnostics/collector.py`)
- HKCU proxy normalization + localhost proxy parsing
- Optional localhost listener attribution + netstat-derived counters
- Interesting process rows sampled from CSV `tasklist`

## Hypotheses (deterministic)

All scores stay in `[0,1]` additive bumps with clamp:

- `unexpected_user_proxy`
- `local_proxy_hijack`
- `browser_proxy_path_issue`
- `localhost_proxy_owner_suspicious`
- `socket_exhaustion`
- `dns_resolution_issue`
- `tls_path_issue`
- `winhttp_proxy_issue`
- `winsock_corruption_possible`
- `isp_router_path_issue`

## Compatibility

Historic `python -m src diagnose` (v1) remains untouched; **`diagnose-live`** writes `reports/last_diagnosis_live.json` and richer JSONL without replacing v1 payloads.

## Hypothesis decisions + Proof Engine (`--proofs`)

`python -m src diagnose-live [--proofs]` adds:

- **`hypothesis_decisions`**: ranked rows shaped as `{ hypothesis, confidence, proof_status, why, decision, risk_score }` with `proof_status` in `CONFIRMED` / `REJECTED` / `INCONCLUSIVE` / `UNPROVEN`.
- **`proof_engine`**: populated when `--proofs` runs (currently `localhost_proxy_https_contrast` for proxy-related hypotheses).
- **`decision_policy`**: summaries rules (ALLOW means safe-tier may proceed with confirmation; destructive actions never auto-run).

Without `--proofs`, every row gets `proof_status=UNPROVEN`; policy still derives `ALLOW`/`PREVIEW`/`BLOCK` from confidence bands.

## Uncertainty (`uncertainty` blob on `last_diagnosis_live.json`)

- **Data trust**: coarse `signal_trust` scores plus `trust_aggregate`; **conflicts** (e.g. HKCU proxy port not in listen set, gateway vs WAN ping).
- **Failure-mode hints**: FN/FP/partial transport labels (heuristic, not ground truth).
- **Degraded mode**: low aggregate, multi-conflict bundle, proof engine exception, or missing proof when `--proofs` was set — **caps CONFIRMED ALLOW → PREVIEW** for safety.
- **Adversarial hints**: cheap string heuristics (`ADV_*`); not forensic claims.
- **Risk** on each `hypothesis_decisions[]` row: `risk_score ≈ confidence × static impact ordinal` from `src/hypothesis/risk.py` (shim: `src/decision_engine/risk_numeric.py`).

## Audit + replay (`logs/decision_runs.jsonl`)

Every successful live run appends **`live_run_audit_v1`** (append-only UTF-8 JSONL):

- **`observations`**: embedded `LiveNetworkSnapshot.to_dict()` (full reproducibility without re-probing).
- **`hypotheses_ranked`**, **`hypothesis_decisions`**, confidences & decisions.
- **`proof_engine`** / **`proof_engine_error`** / **`proofs_requested`**.
- **`uncertainty`** (trust/conflicts/etc.), **`commands_executed`**, snapshot path reference.

**CLI:** Offline replay — `python -m src replay <run_id>` or `python -m src diagnose-live --replay <run_id>` (`run_id` = `diagnosis_id`). Prints an **execution-flow narrative** plus verification flags (re-score from embedded observations, diff confidences/order/decisions vs stored row). **`--json`** emits structured JSON **only** (includes `replay_execution`, `explain`); **`--both`** prints the human summary first then `JSON_PAYLOAD_*` markers around the JSON. Proof curl steps are **not** re-run; causal blobs are archival.

**Live + proof from one entrypoint:** `python -m src diagnose --proof` (or `diagnose --live` without proof) mirrors `diagnose-live` / `diagnose-live --proofs`. **`preview`** / **`repair-preview`** show tiered repair suggestions with optional `--json` or `--both`.
