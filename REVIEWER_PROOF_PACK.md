# Reviewer proof pack

**Purpose:** Commands and contracts for engineering reviewers (platform, security, audit).  
**Status:** Production-shaped **portfolio prototype** — not production-certified.

---

## What this project is

Deterministic **evidence → classification → proof tier → policy gate → remediation preview → audit** pipeline for Windows endpoint reliability and technology risk analytics.

## What this project does **not** claim

- Not antivirus, EDR, or XDR
- Not malware attribution or compromise attestation
- Not MITM confirmation without TLS path proof
- Not autonomous remediation (dry-run / preview-only by default)
- Not SOC 2 or formal audit opinion
- Not AI-authorized execution (AI explains only; policy + human gate remain authoritative)
- Not production fleet scale without gaps in `docs/production-readiness-gap.md`

---

## Prerequisites

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
```

---

## Commands run (reviewer checklist)

| Check | Command | Expected |
|-------|---------|----------|
| **Reviewer contracts** | `pytest -q tests/reviewer/` | All pass |
| **Stability regressions** | `pytest -q tests/reviewer/test_stability_regressions.py` | All pass |
| **Read-only agent + ERP CLI** | `pytest -q tests/windows_network_toolkit/test_read_only_agent.py windows_network_toolkit/tests/test_proxy_cli.py` | All pass |
| **Safety contracts** | `pytest -q tests/test_policy_safety_contract.py tests/security/test_security_review_pack.py` | All pass |
| **Full suite** | `pytest -q` | ~1670+ pass (6 skipped allowed on Linux-only) |
| **Lint** | `ruff check .` | Pass |
| **Typecheck** | `mypy src/platform_core` | Inconclusive if local venv mypy is broken; see below |
| **Docker config** | `docker compose -f docker-compose.demo.yml config` | Valid YAML (not live health) |

### Windows pytest temp note

`pytest.ini` sets `--basetemp=.pytest-tmp` (repo-local; gitignored). An earlier full run on Windows exited code **1** during pytest **teardown** with `PermissionError` on `%LOCALAPPDATA%\Temp\pytest-of-*` — an environment/cleanup issue, not a product defect. A subsequent clean rerun passed fully.

### Mypy note

If local mypy fails with `ModuleNotFoundError: librt.internal`, treat as **venv/tooling corruption** — reinstall mypy in a fresh venv or rely on CI. Do **not** count that as a repo defect until confirmed on a clean environment.

CI scope (`.github/workflows/ci.yml`):

```bash
mypy src/platform_core/ai_risk_analyst src/platform_core/risk src/platform_core/governance --ignore-missing-imports
```

---

## 5-minute live demo (fixture-safe, read-only)

```powershell
# 1. Version (no side effects)
python -m windows_network_toolkit version

# 2. Dead proxy classification (fixture)
python -m windows_network_toolkit proxy-status --fixture examples/evidence/DEAD_PROXY_CONFIG.json
python -m windows_network_toolkit diagnose --proof --fixture examples/evidence/DEAD_PROXY_CONFIG.json

# 3. Governance from audit fixtures
python -m windows_network_toolkit risk-kpi-summary --audit-dir tests/fixtures/risk_analytics/audit_sample --format json
python -m windows_network_toolkit governance-report --audit-dir tests/fixtures/risk_analytics/audit_sample --format markdown

# 4. Reviewer proof tests
pytest -q tests/reviewer/ -v

# 5. API (optional — new terminal)
.\start-api.ps1
# curl http://127.0.0.1:8000/platform/health
```

### Docker reviewer demo (optional — not verified unless you run it)

```powershell
docker compose -f docker-compose.demo.yml up --build
curl http://127.0.0.1:8000/health
```

Only `docker compose config` has been validated in automated reviewer runs unless noted in the pass/fail log below.

See `docs/docker-demo.md`.

---

## Architecture proof points (files to open)

| Claim | Evidence |
|-------|----------|
| Deterministic classification | `src/platform_core/classification/engine.py` (`classify_proxy`) |
| Policy gate authoritative | `src/platform_core/policy/engine.py` (`evaluate_policy`) |
| Proof tiers + limitations | `src/platform_core/governance/proof_tier.py` |
| Audit hash chain | `src/platform_core/governance/chain_of_custody.py` (`verify_chain`) |
| Preview-only rollback | `src/platform_core/remediation/rollback.py` (`can_execute_rollback`) |
| Invalid preview rows surfaced | `src/platform_core/remediation/planner.py` (`invalid_preview_row`) |
| Report mock serialization | `windows_network_toolkit/audit/report_generator.py` (`_json_default`) |
| AI guardrails | `src/platform_core/ai_risk_analyst/explanation_guardrails.py` |
| Safety CI | `tests/test_policy_safety_contract.py`, `tests/security/test_security_review_pack.py` |

---

## Known limitations (honest)

| Area | Limitation |
|------|------------|
| Auth | Demo `/trisk/*` may be open; `X-Api-Role` is not production IdP |
| Audit storage | Local JSONL + hash chain tests — not WORM/object store |
| Agent | Read-only prototype — unsigned, no fleet PKI |
| Scale | Synthetic 10k tests are **local only** (`docs/scale-testing.md`) |
| RAG | Design docs only — not core runtime path |
| Black | ~200 files formatting debt — CI `black --check` is continue-on-error |
| Mypy | Partial scope; CI continue-on-error; local venv may be inconclusive |

Full gap table: `docs/production-readiness-gap.md`

---

## Pass/fail log

Update after each reviewer run. **Do not mark PASS unless the command actually passed.**

```
Date: (fill on run)
pytest -q tests/reviewer/                    : PASS / FAIL
pytest -q tests/windows_network_toolkit/test_read_only_agent.py windows_network_toolkit/tests/test_proxy_cli.py : PASS / FAIL
pytest -q                                    : PASS / FAIL
ruff check .                                 : PASS / FAIL
docker compose -f docker-compose.demo.yml config : PASS / FAIL
mypy src/platform_core                       : PASS / FAIL / MYPY INCONCLUSIVE — local venv/tooling failure
docker live health (optional)                : NOT RUN / PASS / FAIL
```

**Latest clean full pytest rerun (reference):** 1672 passed, 6 skipped (~11m). Earlier Windows teardown `PermissionError` logged separately as environment issue.

---

## Related docs

- `README.md` — positioning and non-claims
- `SYSTEM_DESIGN.md` — architecture
- `docs/security-review.md` — threat model
- `docs/rollback-strategy.md` — preview-first rollback
- `docs/faang-platform-review.md` — platform reviewer pack
- `docs/big4-interview-defense.md` — audit reviewer pack
