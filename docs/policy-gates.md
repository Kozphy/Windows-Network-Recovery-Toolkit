# Policy Gates

**Engine:** `src/platform_core/policy/engine.py` · **YAML:** `config/policy/enterprise_default.yaml`

---

## Gate Definitions

| Gate | Execute | Preview | When |
|------|---------|---------|------|
| **ALLOW** | No | No | Healthy baseline, known dev/security proxy |
| **PREVIEW** | No | Yes | Default for partial evidence; dry-run remediation |
| **BLOCK** | No | No | Destructive actions, low confidence, unsafe tokens |
| **REQUIRE_CONFIRMATION** | No | Yes | Typed phrase required before live apply |
| **REQUIRE_ADMIN** | No | Varies | Elevated operations (not default CLI path) |
| **REQUIRE_HUMAN_REVIEW** | No | Yes | Unknown/suspicious/MITM-adjacent classifications |

Legacy aliases normalized via `src/platform_core/policy/outcome_normalizer.py`: `PREVIEW_ONLY`, `ALLOW_PREVIEW`, `OBSERVE`, `BLOCK_RECOMMENDED`, `ESCALATE_REVIEW`.

---

## Classification → Gate (summary)

| Classification | Typical gate |
|----------------|--------------|
| `NO_PROXY`, `KNOWN_DEV_PROXY`, `KNOWN_SECURITY_TOOL` | ALLOW |
| `DEAD_PROXY_CONFIG`, `WININET_WINHTTP_MISMATCH` | PREVIEW |
| `LOCAL_PROXY_ACTIVE` | PREVIEW or ALLOW |
| `UNKNOWN_LOCAL_PROXY`, `SUSPICIOUS_PROXY`, `POSSIBLE_MITM_RISK` | REQUIRE_HUMAN_REVIEW |
| `REVERTER_SUSPECTED` | REQUIRE_HUMAN_REVIEW |
| `PAC_CONFIGURED` | ALLOW (observe PAC) |
| `ERROR_INSUFFICIENT_DATA` | BLOCK remediation |

---

## Why Preview-Only Is Default

1. **Diagnosis ≠ authorization** — L2 must not mutate registry on observation alone
2. **Enterprise blast radius** — HKCU/HKLM proxy changes affect all user apps
3. **Audit defensibility** — Committee reports require preview hash before apply
4. **Safety contracts** — CI enforces `tests/test_policy_safety_contract.py`

---

## Why Remediation Is Separated from Diagnosis

| Concern | Diagnosis path | Remediation path |
|---------|----------------|------------------|
| Data collection | Read-only collectors | Allowlisted mutations only |
| Output | Classification + limitations | Dry-run plan + confirmation |
| Authority | Any operator | Typed confirm + policy pass |
| Audit | Evidence JSON | Apply row with rollback snapshot |

---

## Safety in Enterprise Endpoint Environments

- No silent process kill, firewall reset, or adapter disable
- No registry mutation without typed confirmation
- API `/platform/remediation/execute` defaults to `dry_run=true`
- AI explains; humans authorize

Tests: `tests/test_policy_safety_contract.py`, `tests/backend/test_policy_yaml.py`

*Legacy:* [policy_model.md](policy_model.md)
