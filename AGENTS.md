# AGENTS.md — agent instructions for this repository

**Windows Network Recovery Toolkit** — local-first Windows endpoint reliability and
technology-risk governance: evidence collection, classification, policy-gated remediation
previews, and append-only audit trails.

**Not:** antivirus, EDR, XDR, malware detector, MITM confirmation system,
autonomous remediation agent, SOC 2 attestation tool, formal audit opinion,
or enterprise-certified production software.


For human onboarding, read [`docs/ONBOARDING.md`](docs/ONBOARDING.md) and
[`docs/DOCUMENTATION_INDEX.md`](docs/DOCUMENTATION_INDEX.md). For docstring style, see
[`docs/code-documentation-standards.md`](docs/code-documentation-standards.md).

Cursor-specific scoped rules (if present): `.cursor/rules/`.

---

## Safety conventions (non-negotiable)

### Epistemic boundaries

1. **Observation is not proof.**
2. **Correlation is not causation.**
3. **Classification is not accusation.**
4. **Confidence is ordinal, not calibrated probability.**
5. **Policy permission is not a safety guarantee.**
6. **Recommendation is not execution authority.**
7. **AI explains only; humans and policy gates authorize actions.**

Preserve `limitations[]` in outputs, reports, explanations, API responses, and audit artifacts. Do not strip uncertainty language.

Do not introduce wording, code paths, documentation, tests, API responses, or demos that imply unsupported certainty, attribution, compromise, malware, confirmed MITM, formal assurance, or production certification.


### Mutation boundaries

- **Dry-run is the default** for registry-changing or state-changing commands.
- **No silent remediation** — live apply requires explicit flags and typed confirmation tokens.
- **Never implement or call** blocked destructive actions (see `windows_network_toolkit/safety.py`):
  - `KILL_PROXY_PROCESS`
  - `FIREWALL_RESET`
  - `ADAPTER_DISABLE`
  - `WINHTTP_MODIFY` (unless an existing, explicit, documented path already allows it)

### Confirmation tokens (live apply)

| Flow | Token | Module |
|------|-------|--------|
| WinINET proxy disable | `DISABLE_WININET_PROXY` | `windows_network_toolkit/safety.py`, `proxy_remediation.py` |
| ChatGPT LOW-risk remediations | `APPLY_CHATGPT_LOW_RISK` | `src/network_recovery/remediation_executor.py` |

Do not weaken confirmation gates, bypass dry-run defaults, or add execution paths that skip audit logging.

### Audit

- Append-only JSONL under `.audit/` and `logs/` (e.g. `logs/network_recovery_events.jsonl`).
- Mutation and recommendation paths should remain auditable.
- Agents and planners must **not** auto-execute repairs; recommend preview/read-only steps only unless the user explicitly requests apply with the correct token.

### Gold-standard safety modules (read before changing remediation)

- `windows_network_toolkit/proxy_remediation.py`
- `windows_network_toolkit/proxy_guardian.py`
- `windows_network_toolkit/safety.py`
- `src/network_recovery/remediation_executor.py`

---

## CLI conventions

### Primary entrypoint

```powershell
python -m windows_network_toolkit <command> [options]
```

Use this for **new work**. `python -m src` is a legacy shim — avoid adding new commands there.

### Environment (repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
```

`requirements.txt` installs editable `.[dev]` (includes `sqlmodel`, pytest, ruff).

### Fixture-first development (preferred in tests and CI)

```powershell
python -m windows_network_toolkit analytics-summary `
  --fixture tests/fixtures/analytics_pipeline_fixture.json --json
```

Use `--fixture` paths under `tests/fixtures/` or `examples/` — no admin, no host mutation.

### Command groups (high level)

| Group | Examples |
|-------|----------|
| Evidence | `proxy-status`, `proxy-health`, `diagnose`, `evidence-report` |
| Proof | `proxy-proof`, `tls-proof`, `bad-gateway-diagnose` |
| Remediation | `proxy-disable` (dry-run default), `auto-fix-chatgpt` |
| Agent (read-only) | `agent once`, `agent run`, `agent health`, `agent spool-status` |
| Analytics | `analytics-summary`, `analytics-export`, `powerbi-export` |
| Governance | `risk-assess`, `control-test`, `governance-report`, `audit verify` |
| LAN privacy | `lan-inventory`, `lan-watch`, `lan-privacy-report` |
| AI evals | `ai-eval` (fixture-only, no live model calls) |

Full argparse: `windows_network_toolkit/cli.py`. Operator scripts: `scripts/` (e.g. `auto-fix-proxy.ps1`, `auto-fix-chatgpt.ps1`).

### Makefile shortcuts

```powershell
make install          # pip install -r requirements.txt
make demo             # golden fixture replay (~3 min)
make principles-test  # fast epistemic/safety contract tests
make test             # full pytest suite (~10 min)
make fix-chatgpt      # Windows: policy-gated ChatGPT auto-fix chain
```

---

## Test conventions

### Run tests

```powershell
# Full suite (~10 min)
pytest -q

# Or: ensure deps + pytest via project venv
.\scripts\pytest.ps1 -q

# Targeted (preferred while iterating)
pytest -q tests/test_network_recovery_auto_fix.py
make principles-test
```

### Requirements

- Project venv must have deps installed: `pip install -r requirements.txt`
- Root `conftest.py` fails fast with install hints if `sqlmodel` or native wheels are missing
- Config: `pytest.ini` — `testpaths = tests windows_network_toolkit/tests`, `--import-mode=importlib`, `-p no:schemathesis`

### Writing tests

- Prefer **fixtures** over live Windows registry/network probes in new tests
- Mark true OS integration with `@pytest.mark.linux_integration` only under `tests/integration_linux/`
- Do not change test assertions to match broken behavior — fix the code or fixture
- Safety contract tests: `tests/test_policy_safety_contract.py`, `tests/test_safety_contract_extensions.py`, `make principles-test`
- After remediation or policy changes, run the relevant area tests plus a principles/safety slice before claiming done

### Lint (touched Python paths)

```powershell
ruff check <paths>
```

---


## AI and agent boundaries

### Agents may help with:

* reading code
* proposing small patches
* adding tests
* improving documentation
* summarizing evidence
* drafting safer explanation text
* identifying missing verification steps

### Agents must not:

* authorize registry changes
* execute remediation without explicit user instruction and required confirmation tokens
* bypass policy gates
* weaken dry-run defaults
* remove audit logging
* convert correlation into attribution
* describe classifications as malware, compromise, or confirmed MITM
* claim SOC 2 assurance, regulatory attestation, or enterprise production certification

For risky or accusatory-adjacent outputs, preserve `limitations[]` and prefer preview/read-only guidance.


## Implementation guidance for agents

1. **Minimize scope** — match surrounding code; reuse existing functions; no unrelated refactors.
2. **Read one similar module** before adding new behavior (see gold-standard list above).
3. **Do not load portfolio-only docs** (`big4-interview-*`, pitch scripts) unless the user asks — use `docs/ONBOARDING.md` and flow docs (`chatgpt-auto-fix.md`, `dead-proxy-guardian.md`, `ai-evals-feedback-loop.md`).
4. **Documentation-only tasks** — follow `docs/code-documentation-standards.md`; no logic/signature changes unless requested.
5. **Commits** — only when the user explicitly asks; never commit `.env`, secrets, or `__pycache__/`.

---

## Reviewer proof expectations

When preparing changes for portfolio review, prefer evidence over claims:

* `pytest` should pass, or failures should be documented honestly.
* `ruff` should pass for touched Python files.
* Demo commands should be reproducible from repo-root instructions.
* Fixture-based examples should avoid live host mutation.
* Safety, policy, audit, and explanation-boundary tests should not be weakened.
* `docs/REVIEWER_PROOF_PACK.md`, if present, must reflect commands that actually exist and results that were actually observed.

Do not claim that tests, demos, CI, replay, audit verification, or production readiness are complete unless verified.

---

## Key paths

| Path | Role |
|------|------|
| `windows_network_toolkit/` | Primary CLI and Windows diagnostics |
| `src/network_recovery/` | ChatGPT app-path diagnose + LOW-risk auto-fix |
| `src/platform_core/` | Governance, proof, audit, ai_evals |
| `backend/` | FastAPI platform API |
| `tests/fixtures/` | Deterministic demo and test inputs |
| `mcp_server/` | Read-only MCP tools (no remediation execute) |
