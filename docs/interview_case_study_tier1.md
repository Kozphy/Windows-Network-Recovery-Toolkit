# Interview case study (Tier-1)

## STAR

**Situation:** Windows endpoints reported browser and dev-tool HTTPS failures while ping and DNS appeared healthy. Operators suspected “network is fine” but WinINET proxy settings had drifted to stale localhost listeners or unexpected external proxies.

**Task:** Build a **local-first endpoint reliability platform** that explains failures safely — without autonomous kill, firewall reset, or silent registry mutation.

**Action:**
- Probes for WinINET/WinHTTP, DNS, ping, browser path
- Event normalization → evidence fusion with explicit levels (`OBSERVED_ONLY` … `FINAL_CAUSATION`)
- Reasoning + policy gates (`PREVIEW_ONLY`, `REQUIRE_TYPED_CONFIRMATION`, …)
- Remediation **preview** with `dry_run=true` default on API execute
- Append-only JSONL audit + deterministic replay
- FastAPI `/platform/*`, optional Next.js dashboard, Prometheus `/metrics`
- Synthetic fleet demo (100 endpoints, 20 incidents) and fixture regression tests

**Result:** The system explains proxy/browser-path failures, blocks unsafe automated repair, distinguishes correlation from proof, replays incidents deterministically, and demonstrates enterprise-style endpoint reliability workflows in CI without Windows admin.

## Technical tradeoffs

| Choice | Why |
|--------|-----|
| JSONL not Postgres by default | Local-first, portfolio-friendly, replayable |
| Ordinal confidence | Honest epistemics vs fake probabilities |
| Preview-only default | Safety over automation speed |
| Fixture-heavy CI | Linux agents without live registry mutation |

## Intentionally not automated

- Process kill, firewall reset, adapter disable
- Autonomous containment or malware removal
- Cloud telemetry upload by default
- Production auth (demo RBAC headers only)

## Scale to 10,000 endpoints

- Partition JSONL by endpoint hash or move to managed Postgres (`platform_core/db/`)
- Agent pull model with mTLS; batch ingest via `/platform/v3/fleet/*`
- Incremental metrics counters vs full JSONL scans

## Auth / RBAC

- Replace `X-Operator-*` headers with Entra ID / API keys
- Separate viewer / operator / admin roles per route (see `docs/rbac_and_remediation.md`)

## EDR / SIEM integration

- Export normalized events and audit JSONL to SIEM (opt-in)
- Ingest Sysmon/Procmon from existing agents — do not duplicate EDR

## False positives

- Track `incident_false_positive` signals and `proof_unavailable_rate` SLO
- Case study `003_remediation_not_sticky` for active reverters
- Developer allowlist with continued logging
