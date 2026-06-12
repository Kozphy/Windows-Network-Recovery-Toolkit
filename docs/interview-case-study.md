# Interview case study: Endpoint Reliability Platform

Portfolio narrative for platform engineering, SRE, and cyber risk roles. Anchor on the **59081 dead proxy** golden path.

---

## Elevator pitch (30 seconds)

I built a **local-first endpoint reliability platform** that turns messy Windows network failures into structured evidence: observation → classification → proof → policy → remediation preview → audit. It is not an antivirus or autonomous repair bot. It enforces **diagnose before remediate**, blocks destructive actions by default, and documents what we **cannot** prove.

---

## STAR: dead localhost proxy (127.0.0.1:59081)

| | |
|---|---|
| **Situation** | User reports "internet works for ping but browsers fail." WinINET shows `ProxyEnable=1`, `ProxyServer=127.0.0.1:59081`. WinHTTP is direct. No listener on 59081. |
| **Task** | Classify root cause tier, produce auditable proof, allow only safe remediation. |
| **Action** | `proxy-status` → `DEAD_PROXY_CONFIG` + `WININET_WINHTTP_MISMATCH`. `diagnose --proof` → supported. Policy allows `DISABLE_WININET_PROXY` with typed token. Applied via JSON CLI with before/after audit in `.audit/`. |
| **Result** | Browser path restored. Incident report shows limitations (no malware/MITM claims). Reverter watch available if proxy reappears. |

Full write-up: [case-studies/dead-localhost-proxy.md](case-studies/dead-localhost-proxy.md)

---

## Architecture decisions (why not a script)

| Script anti-pattern | Platform choice |
|---------------------|-----------------|
| One registry reset | Policy-gated preview + typed confirmation |
| Heuristic = guilt | 12 primary classifications + confidence 0–1 |
| Silent fixes | Append-only `.audit/*.jsonl` |
| Laptop-only | Fixture-safe CI on Linux + Windows live probes |

**Primary CLI:** `python -m windows_network_toolkit` (JSON-first)  
**Legacy shim:** `python -m src` (stderr deprecation notice on proxy commands)

Canonical engines live in `src/platform_core/`; Windows probes in `windows_network_toolkit/` facades.

---

## Safety model (memorize for interviews)

1. **Observation ≠ proof** — registry state is not causation.
2. **Correlation ≠ causation** — listener match ≠ registry writer.
3. **Confidence is 0–1 ordinal** — not Bayesian malware probability.
4. **Policy permission ≠ safety guarantee** — rollback + audit still required.

Blocked by default: process kill, firewall reset, adapter disable, WinHTTP mutation.

Tests: `tests/windows_network_toolkit/test_safety_contract.py`

---

## Proof vs observation (one-liner)

> Observation records what we saw. Proof records what we **tested** and whether the hypothesis survived those tests.

See [proof-vs-observation.md](proof-vs-observation.md).

---

## Enterprise relevance

| Audience | Angle |
|----------|-------|
| Big 4 cyber risk | Evidence tiers, audit trail, explicit limitations — [big4-cyber-risk-positioning.md](big4-cyber-risk-positioning.md) |
| FAANG platform eng | Facade/core split, JSON CLI contract, CI matrix — [faang-platform-engineering-positioning.md](faang-platform-engineering-positioning.md) |
| SRE | MTTR reduction via structured triage, replay determinism |
| Security | MITM heuristics require ≥2 independent indicators |

---

## Demo commands (fixture-safe, no admin)

```powershell
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit proxy-disable --dry-run
python -m windows_network_toolkit proxy-report --fixture tests/fixtures/enert/dead_proxy_59081.json
```

Script: [three-minute-demo-script.md](three-minute-demo-script.md)

---

## Honest limitations (credibility)

- Registry writer attribution needs Sysmon E13 or equivalent for high-confidence causation.
- Website/TLS risk engines are heuristic, not EDR-grade.
- Fleet scale, RBAC, signed packaging are roadmap items.
- Linux CI runs fixture/mocked paths; live probes require Windows.

See [production-readiness.md](production_readiness.md).

---

## Related docs

- [classification-model.md](classification-model.md)
- [safety_model.md](safety_model.md)
- [evidence_model.md](evidence_model.md)
- [demo_5_min.md](demo_5_min.md)
