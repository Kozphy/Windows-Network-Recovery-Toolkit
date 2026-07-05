# Security review pack

**Status:** Portfolio / pre-production security posture — local-first endpoint reliability platform.  
**Audience:** Internal audit, IT risk, platform engineering, security reviewers.  
**Last reviewed:** Phase 7 enterprise hardening.

**Related:** [threat-model.md](threat-model.md) · [security_boundaries.md](security_boundaries.md) · [security-abuse-cases.md](security-abuse-cases.md) · [AGENTS.md](../AGENTS.md)

---

## Executive summary

This toolkit is a **local-first evidence and policy-gated remediation preview** system. It is **not** antivirus, EDR, XDR, or autonomous containment. Security design prioritizes:

1. **Dry-run by default** for state-changing operations  
2. **Typed human confirmation** before allowlisted registry/network mutations  
3. **Hard-blocked destructive actions** (process kill, firewall reset, adapter disable, WinHTTP modify)  
4. **AI advisory only** — models cannot authorize execution  
5. **Append-only hash-chained audit** for tamper detection on local JSONL  
6. **Explicit limitations[]** on classifications and exports  

---

## 1. Assets

| Asset | Location / form | Sensitivity |
|-------|-----------------|-------------|
| Endpoint proxy/registry observations | CLI output, spool JSONL, `platform_data/` | Operational — may reveal misconfig |
| Audit / decision JSONL | `logs/`, `.audit/`, `platform_data/audit.jsonl` | Governance — tamper-evident |
| Agent spool | `.audit/agent-spool.jsonl` | Read-only evidence rows |
| Policy / remediation registry | `platform_core/remediation_registry.py` | Integrity — defines allowlist |
| API tokens (demo) | Env / headers `X-Api-Token` | **Secrets** — must not commit |
| Hash chain tips | `current_hash` per audit row | Integrity anchor |
| Fixture / synthetic fleet data | `tests/fixtures/` | Low — labeled synthetic |
| Operator confirmation phrases | Code + docs | Safety control — not secret per se |

**Out of scope as trusted assets:** Remote SIEM, WORM storage, HSM-backed signing (future hardening).

---

## 2. Trust boundaries

```text
┌─────────────────────────────────────────────────────────────────┐
│  Operator / human reviewer (trusted for confirmation tokens)     │
└────────────────────────────┬────────────────────────────────────┘
                             │ typed confirmation / CLI intent
┌────────────────────────────▼────────────────────────────────────┐
│  CLI (wnrt / python -m windows_network_toolkit)                  │
│  Policy engine · safety.py BLOCKED_ACTIONS · dry-run default       │
└────────────────────────────┬────────────────────────────────────┘
                             │ allowlisted argv only
┌────────────────────────────▼────────────────────────────────────┐
│  Host OS (registry, netsh, subprocess) — UNTRUSTED side effects    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  FastAPI backend (optional, local/demo)                          │
│  RBAC headers = UNSIGNED demo simulation — NOT production IdP    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  AI risk analyst / evals — ADVISORY ONLY                         │
│  enforce_advisory_only() strips execution authority              │
└─────────────────────────────────────────────────────────────────┘
```

| Boundary | Trust assumption |
|----------|------------------|
| Operator → CLI | Human supplies confirmation; CLI validates exact phrase |
| CLI → OS | Only allowlisted commands after policy ALLOW + confirm |
| API client → backend | Demo RBAC headers — treat as **no auth** in production |
| AI → remediation | **Never trusted** for execute authority |
| External content → AI prompts | Untrusted — guardrails block unsafe language |

---

## 3. Threat model (summary)

| Threat actor | Goal | Primary controls |
|--------------|------|------------------|
| Mistaken operator | Auto-apply destructive fix | Dry-run default, typed confirmation, BLOCKED_ACTIONS |
| Malicious API caller | Force execute via HTTP | Policy gate `execute_allowed=False`; forbidden action registry |
| Over-trusting AI output | Execute because model said "safe" | `enforce_advisory_only`, explanation guardrails |
| Auditor / attacker with file access | Alter historical decisions | Hash-chained audit `verify_chain()` |
| Prompt injection | Bypass policy via AI narrative | `validate_explanation_text`, malware/kill language blocks |
| Supply-chain attacker | Compromise dependencies | pip-audit/bandit in dev deps; pin in CI |
| Insider | Exfiltrate tokens from logs | 401 responses must not echo tokens |

Full tables: [threat-model.md](threat-model.md), [threat_model.md](threat_model.md).

---

## 4. Abuse cases

| # | Abuse case | Expected behavior | Tests |
|---|------------|-------------------|-------|
| A1 | Call `proxy-disable` without `--dry-run false` + token | Preview only, no registry write | `test_safety_contract.py`, security review pack |
| A2 | POST fake execute to API | 404/405/422 — no execute route | `tests/security/test_policy_bypass_blocked.py` |
| A3 | AI says "execute automatically" | Authority downgraded to `human_required` | `test_security_review_pack.py`, governance contracts |
| A4 | Classify listener PID as malware | Limitations state correlation ≠ proof | `test_non_claim_regression.py` |
| A5 | Replay tampered audit row | `verify_chain` fails at index | `test_audit_tamper_detection.py` |
| A6 | Duplicate evidence ingest | Idempotent event_id (v1 API) | `tests/security/test_abuse_cases.py` |
| A7 | Shell injection in confirmation | `is_shell_injection` rejects | `tests/policy/test_safety_boundaries.py` |
| A8 | Viewer role attempts live execute | Blocked | `test_safety_boundaries.py` |

More: [security-abuse-cases.md](security-abuse-cases.md).

---

## 5. Dangerous actions (hard-blocked)

Canonical registry: `windows_network_toolkit/safety.py`

| Action ID | Blocked | Rationale |
|-----------|---------|-----------|
| `KILL_PROXY_PROCESS` | Yes | No silent process termination |
| `FIREWALL_RESET` | Yes | Network-wide impact |
| `ADAPTER_DISABLE` | Yes | Denial of connectivity |
| `WINHTTP_MODIFY` | Yes | System proxy stack — explicit path only |

Platform policy mirrors via forbidden keys: `process_kill_forbidden`, `reset_firewall`, `adapter_disable_forbidden`, `arbitrary_command_forbidden`.

`DEMO_MODE` env treats **all** actions as blocked for reviewer demos.

---

## 6. Policy gates

| Layer | Module | Outcomes |
|-------|--------|----------|
| WNT facade | `windows_network_toolkit/platform/policy.py` | `allowed`, `requires_confirmation` |
| Platform core | `platform_core/policy.py` | `execute_allowed`, `preview_allowed`, `reason_codes` |
| Hypothesis | `src/policy/hypothesis_gates.py` | ALLOW / PREVIEW / BLOCK by proof tier |
| Remediation registry | `platform_core/remediation_registry.py` | Per-action `requires_confirmation`, `confirmation_phrase` |
| API | `backend/platform_routes.py` | Dry-run default, RBAC surfaces |

**Rule:** `preview_allowed` does **not** imply `execute_allowed`. Operator role may preview; admin execute still needs confirmation phrase for gated actions.

---

## 7. Local file permissions

| Path | Git | Permissions guidance |
|------|-----|----------------------|
| `.env`, `.env.local` | **Ignored** | Operator-only read; never commit |
| `platform_data/` | Ignored | Local JSONL — restrict ACL to service account |
| `logs/`, `.audit/` | Often ignored | Append-only audit — backup for integrity |
| `tests/fixtures/` | Committed | Synthetic — safe to share |

Repository `.gitignore` excludes secrets and runtime data. Production deployments should:

- Run read-only agent under least-privilege account  
- Restrict write access to spool/audit directories  
- Not run API on `0.0.0.0` without TLS + real auth (out of repo scope)

---

## 8. Audit tamper detection

Implementation: `src/platform_core/governance/chain_of_custody.py`, `src/platform_core/audit/writer.py`

- Each record: `previous_hash` → `current_hash` (SHA-256 over canonical body)  
- CLI: `python -m windows_network_toolkit audit verify <path.jsonl>`  
- Tampering with payload breaks chain at first altered index  

**Proves:** post-hoc edit detection on local JSONL.  
**Does not prove:** completeness, off-tool actions, or append-only forgery without external anchor.

Tests: `tests/platform_core/governance/test_audit_tamper_detection.py`, `tests/test_governance_safety_contracts.py`.

---

## 9. Dependency / supply-chain risks

| Risk | Mitigation in repo |
|------|-------------------|
| Vulnerable PyPI packages | `pip-audit` in `[dev]` optional deps |
| Static analysis gaps | `bandit`, `ruff` in CI/dev |
| Unpinned transitive deps | `requirements.txt` + lock discipline (operator) |
| Malicious post-install scripts | Prefer `pip install` from known wheel; review `pyproject.toml` |

**Gap:** No signed wheel / SBOM in release pipeline (see [packaging-installer.md](packaging-installer.md) future work).

---

## 10. Secrets handling

| Secret type | Handling |
|-------------|----------|
| API tokens | Env vars; `.env` gitignored; `test_no_secret_leakage.py` — 401 must not echo token |
| Stripe / DB URLs | Env only — not in fixtures |
| Confirmation phrases | Documented in code — safety control, not authentication secret |
| JWT demo keys | Local dev only — not production |

Operators: use `.env.example` as template; rotate tokens if leaked; never paste tokens into audit JSONL.

---

## 11. Safe defaults

| Control | Default |
|---------|---------|
| `proxy-disable` | `dry_run=True` |
| `evaluate_policy` | `dry_run=True` |
| Agent loop | Read-only, no remediation |
| Service install | **Not** registered by pip/pipx (documented opt-in only) |
| `PLATFORM_FIXTURE_MODE` | Backend demo may enable fixtures — not production |
| AI execution authority | `preview_only` / `human_required` after sanitization |
| Blocked destructive actions | Denied regardless of confidence |

---

## 12. Non-claims

This platform **does not**:

- Detect or remove malware  
- Replace EDR/XDR/antivirus  
- Prove MITM or compromise without appropriate telemetry tiers  
- Guarantee endpoint safety after remediation preview  
- Provide production-grade multi-tenant authentication in demo API mode  
- Autonomously kill processes, reset firewalls, or disable adapters  
- Treat AI narrative as authorization to execute  
- Claim Linux/macOS WinINET/WinHTTP parity ([cross-platform-support.md](cross-platform-support.md))  

Classifications are **triage labels** with mandatory `limitations[]` — not accusations.

---

## 13. Test contract map (CI)

Run the full safety slice:

```powershell
pytest -q tests/security/test_security_review_pack.py
pytest -q tests/test_policy_safety_contract.py
pytest -q tests/policy/test_safety_boundaries.py
pytest -q tests/test_governance_safety_contracts.py
pytest -q tests/windows_network_toolkit/test_safety_contract.py
pytest -q tests/security/
pytest -q tests/platform_core/governance/test_audit_tamper_detection.py
```

| Requirement | Primary test file |
|-------------|-------------------|
| Registry mutation blocked by default | `test_security_review_pack.py`, `test_safety_contract.py` |
| Process kill blocked | `test_security_review_pack.py`, `BLOCKED_ACTIONS` |
| Firewall reset blocked | `test_security_review_pack.py`, `test_safety_boundaries.py` |
| Adapter disable blocked | `test_security_review_pack.py` |
| AI cannot authorize execution | `test_security_review_pack.py`, `test_governance_safety_contracts.py` |
| Classifications include limitations | `test_security_review_pack.py`, portfolio evidence suite |
| Typed human confirmation | `test_security_review_pack.py`, policy safety contract |
| Audit tamper detection | `test_audit_tamper_detection.py` |

---

## 14. Review checklist (human)

- [ ] Confirm `DEMO_MODE` / `PLATFORM_SAFE_MODE` documented for reviewer environments  
- [ ] Confirm production API will replace unsigned RBAC headers  
- [ ] Confirm audit JSONL backup and verify run before governance export  
- [ ] Confirm operators trained on confirmation phrases vs blocked actions  
- [ ] Confirm AI outputs reviewed before any live apply  
- [ ] Run CI safety slice before release tag  

---

## 15. Gaps and future work

- Formal penetration test (out of repo scope)  
- WORM / external hash anchor for audit chain  
- Production IdP integration for API  
- Signed release artifacts and SBOM  
- Agent-side double-confirmation for fleet deploy  

See [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) Phases 7–8.
