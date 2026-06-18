# Portfolio Case Study 1: Dead WinINET localhost proxy

## Scenario

A user reports `ERR_PROXY_CONNECTION_FAILED` in the browser. Ping and DNS succeed. IT suspects “network down” or security suspects compromise.

## Evidence

- WinINET `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081`
- No listener bound on port 59081
- WinHTTP may show direct access (stack divergence)
- Proof contrast: direct path healthy; proxied path fails

**Fixture:** `tests/fixtures/case_studies/case_1_dead_wininet_proxy.json`

## Classification

**DEAD_PROXY_CONFIG** (secondary: `WININET_WINHTTP_MISMATCH`, `DEAD_LOCALHOST_PORT`)

## Proof tier

**T1_LOCAL_CONFIG_EVIDENCE** → **T2_RUNTIME_CORROBORATION** when path proof supports dead-proxy hypothesis.  
Capped below T3 for dead-proxy-without-listener unless behavioral reproduction is explicitly recorded.

## Risk rating

Residual **medium** — high user impact, moderate control effectiveness with preview-only remediation.

## Recommended action

`DISABLE_WININET_PROXY` — **preview only**, typed confirmation required, rollback plan documented.

## Safety boundary

- No registry apply without confirmation phrase
- No process kill, firewall reset, or adapter disable
- Classification is triage — **not** malware or MITM confirmation

## Audit record

`RiskDecisionRecord` captures `evidence_hash`, `execution_authority: preview_only`, `human_review_required: true`, and linked `audit_id`.

## Governance report excerpt

> During the review period, dead-proxy incidents drive browser connectivity failures while basic network checks appear healthy. Remediation remains preview-only; human review required before apply.

## Interview talking point

“I separate **observation from proof**: dead registry config is T1 config evidence; listener check upgrades to T2 runtime corroboration. I never jump to compromise language without tier and independent validation.”
