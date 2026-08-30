# Open Source Readiness Checklist

Use this checklist before making the repository public, promoting a release, or accepting external contributions.

**License:** AGPL-3.0-only — see [LICENSE](../LICENSE) and [provenance-and-attribution.md](provenance-and-attribution.md).

---

## 1. Secrets and credentials

| Check | Command / action | Expected |
|-------|------------------|----------|
| No tracked `.env` with real keys | `git ls-files \| findstr /i "\.env$"` | Only `*.example` files (if any) |
| No tracked bytecode junk | `git ls-files \| findstr /i "__pycache__ \.pyc$"` | Empty |
| Pre-commit secret scan installed | `pre-commit install` | Hook registered |
| Gitleaks passes on staged files | `pre-commit run gitleaks --all-files` | Pass |
| Private keys blocked | `pre-commit run detect-private-key --all-files` | Pass |
| Full history scan (manual, periodic) | `gitleaks detect --source . --config .gitleaks.toml -v` | No unexpected leaks |
| Rotate keys if history ever leaked | — | All production keys rotated |

**Never commit:** `.env`, `.env.local`, API keys, JWT secrets, Stripe live keys, customer hostnames in raw exports, unredacted `.audit/` or `reports/`.

---

## 2. Git hygiene

| Check | Action |
|-------|--------|
| `.gitignore` covers runtime artifacts | `__pycache__/`, `.audit/`, `reports/`, `logs/`, `platform_data/`, `*.jsonl` (except fixtures) |
| Remove accidentally tracked `.pyc` | `git rm --cached -r path/to/__pycache__` then commit |
| No local DB or logs in index | `git ls-files \| findstr /i "\.db$ \.log$ \.jsonl$"` — only allowed fixture paths |

---

## 3. Safety and epistemic boundaries

Document clearly in README and docs:

- **Not** antivirus, EDR, XDR, malware attribution, or offensive tooling
- Observation ≠ proof; correlation ≠ causation
- Remediation is **dry-run / preview by default**
- Typed confirmation tokens required for live apply
- Purple Team scenarios are **fixture-first**, deny-by-default, lab-safe

See: [safety_model.md](safety_model.md), [purple_team/safety-model.md](purple_team/safety-model.md), [AGENTS.md](../AGENTS.md).

---

## 4. Tests and CI

| Check | Command |
|-------|---------|
| Safety contracts | `pytest -q tests/test_policy_safety_contract.py` |
| Secret leakage (API) | `pytest -q tests/security/test_no_secret_leakage.py` |
| Purple fixture smoke | `pytest -q tests/purple_team` |
| Full CI gate | Push PR and verify `.github/workflows/ci.yml` |

Privileged host-changing scenarios must **not** run in generic CI — fixtures/mocks only.

---

## 5. Documentation for external readers

| Doc | Purpose |
|-----|---------|
| [README.md](../README.md) | Positioning, non-claims, quick start |
| [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | Full map |
| [purple-team-upgrade-report.md](purple-team-upgrade-report.md) | Purple platform story |
| [provenance-and-attribution.md](provenance-and-attribution.md) | AGPL obligations and fork attribution |
| [SECURITY.md](../SECURITY.md) | Responsible disclosure (if present) |

---

## 6. Pre-commit setup (developers)

```powershell
pip install -e ".[dev]"
pre-commit install
pre-commit run --all-files
```

Hooks include: whitespace/YAML checks, **detect-private-key**, **gitleaks**, ruff, black, scoped mypy, offline pytest safety slice.

---

## 7. Before first public announcement

- [ ] Run full `gitleaks detect` on repository **including history**
- [ ] Confirm no real customer data in `real_evidence/` (samples only)
- [ ] Replace demo API keys in any deployed environment
- [ ] README states AGPL and responsible-use limits
- [ ] Optional: enable GitHub secret scanning / dependabot on the remote repo

---

## Limitations

- Pre-commit gitleaks scans **current tree and commits at hook time**; it does not replace a full history audit.
- `.gitleaks.toml` allowlists documented test placeholders — do not add real secrets to allowlist.
- Tamper-evident custody (`.audit/`) is not WORM storage — document trust assumptions.
