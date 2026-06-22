# Safety Model

**Canonical safety doctrine** for the Technology Risk & Control Analytics Platform.

Principles: no silent registry changes; no silent process killing; no silent firewall reset; no adapter disable; preview-only by default; observation is not proof.

---

## Allowed by Default (Read-Only)

- Read WinINET / WinHTTP registry and `netsh` excerpts
- Run proxy health probes and path contrasts
- Classify evidence and generate governance reports
- Export CSV / Power BI star-schema tables
- Verify audit hash chains and replay fixtures

## Blocked by Default

- Registry mutation without typed confirmation
- Live `proxy-disable` apply without dry-run review
- Process kill, firewall reset, adapter disable
- Autonomous remediation narratives
- Malware / MITM verdicts without limitations
- AI-authorized execution

## Required for Sensitive Actions

- Explicit `--dry-run false` intent
- Typed confirmation token (`DISABLE_WININET_PROXY`, etc.)
- Policy decision recorded in audit log
- Limitation disclosure in output

## Preview vs Execute

| Mode | Registry write | Audit row |
|------|----------------|-----------|
| Preview (`dry_run=true`) | No | Preview requested |
| Execute | Yes (allowlisted only) | Apply + rollback snapshot |

## Allowlisted Actions

| action_id | Confirmation | Reversible |
|-----------|--------------|------------|
| `disable_wininet_proxy` | `DISABLE_WININET_PROXY` | Yes (LKG snapshot) |

## CI Enforcement

```powershell
pytest -q tests/test_policy_safety_contract.py tests/policy/test_safety_boundaries.py
```

*Full detail preserved in legacy sections below.*

---

## Diagnose Before Remediate

- Prefer targeted fixes over full reset
- Ask before applying repairs
- Keep firewall reset manual
- Keep logs local

## Read-Only Operations

`ping`, `nslookup`, `curl`, proxy registry reads, `proxy-status`, `diagnose` (without apply flags).

## Repair Operations (Require Admin + Confirmation)

DNS flush, Winsock reset, WinHTTP reset, firewall reset — **not default CLI behavior**.

---

*Legacy path:* [safety_model.md](safety_model.md) — extended operator guidance retained there.
