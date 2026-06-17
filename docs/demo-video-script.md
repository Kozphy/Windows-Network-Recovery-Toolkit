# Demo Video Script

## Audience

Recruiter · IT manager · Big 4 risk consultant · platform/SRE interviewer

## Goal

Show how the toolkit turns a vague network problem ("browser won't connect") into an **evidence-based diagnosis** and **safe remediation workflow** — without over-claiming certainty or performing destructive actions automatically.

---

## Video Flow

### Scene 1: Problem

**On screen:** Browser showing `ERR_PROXY_CONNECTION_FAILED`. Terminal showing successful `ping` and `nslookup`.

**Voiceover:**
> "This laptop looks online — ping works, DNS resolves — but the browser fails. That's a classic WinINET proxy path problem, not necessarily a network outage. We need evidence before we change anything."

**Commands (optional live check):**

```powershell
ping 8.8.8.8
nslookup example.com
```

---

### Scene 2: Diagnosis

**On screen:** Terminal running toolkit commands; JSON output highlighted.

**Voiceover:**
> "I'll run the endpoint reliability toolkit. It reads proxy settings, checks for localhost listeners, and classifies risk — all read-only by default."

```powershell
cd Windows-Network-Recovery-Toolkit
pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path

python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Highlight in JSON:**

- `classification`: `DEAD_PROXY_CONFIG`
- `secondary_signals`: `WININET_WINHTTP_MISMATCH`
- `confidence`: ~0.92
- `limitations[]`: "Does not prove malware or MITM."

```powershell
python -m windows_network_toolkit proxy-owner --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Voiceover:**
> "No process is listening on the configured port. That's correlation with browser failure — not proof of who wrote the registry."

---

### Scene 3: Evidence Chain

**On screen:** Split view — terminal + simple diagram (Observation → Hypothesis → Proof → Policy → Action → Audit).

**Voiceover:**
> "Observation is not proof. The toolkit runs structured contrast checks before recommending remediation."

```powershell
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
```

**Highlight:**

- `proof_attempts[]` with pass/fail
- `conclusion.status`: `supported`
- `limitations[]` always present

```powershell
python -m windows_network_toolkit proxy-timeline --audit-only
python -m toolkit replay windows_network_toolkit/examples/proxy_drift_incident.jsonl
```

**Voiceover:**
> "Timeline merge shows when proxy settings drifted relative to browser failure. This supports audit and post-incident replay."

---

### Scene 4: Safe Remediation

**On screen:** Dry-run output; confirmation prompt; `.audit/` folder.

**Voiceover:**
> "Dry-run is the default. The toolkit never silently kills processes, resets firewall, or disables adapters. Registry changes require a typed confirmation token."

```powershell
python -m windows_network_toolkit proxy-disable --dry-run
```

**Highlight:**

- `dry_run: true`
- Planned HKCU changes shown as preview
- No host mutation

```powershell
# Only show on Windows after operator review — do not run live in demo unless intentional
python -m windows_network_toolkit proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY
```

**Voiceover:**
> "When applied, every change is appended to an audit JSONL file. We can verify the hash chain later."

```powershell
python -m windows_network_toolkit proxy-report --fixture tests/fixtures/enert/dead_proxy_59081.json
```

---

### Scene 5: Business Value

**On screen:** Incident report summary; optional dashboard at `http://127.0.0.1:8000/dashboard/`.

**Voiceover:**
> "This reduces unsafe manual fixes, improves evidence for IT risk and security review, and gives platform teams deterministic replay for incident postmortems. It indicates likely proxy drift — it does not guarantee the endpoint is clean."

**Optional API demo:**

```powershell
uvicorn backend.main:app --reload
# Open http://127.0.0.1:8000/docs → POST /platform/remediation/preview
```

---

## 3-Minute Version

| Time | Scene | Action |
|------|-------|--------|
| 0:00–0:30 | Problem | Show browser error + ping OK |
| 0:30–1:15 | Diagnosis | `proxy-status --fixture dead_proxy_59081.json` |
| 1:15–1:45 | Proof | `diagnose --proof --fixture ...` — highlight limitations |
| 1:45–2:15 | Safe fix | `proxy-disable --dry-run` only |
| 2:15–3:00 | Value | `proxy-report --fixture ...` + closing voiceover |

**Closing line:**
> "Evidence first, policy-gated action second, audit always."

---

## 5-Minute Version

| Time | Scene | Action |
|------|-------|--------|
| 0:00–0:45 | Problem | Browser fail + ping/DNS OK; explain WinINET vs WinHTTP |
| 0:45–1:45 | Diagnosis | `proxy-status`, `proxy-owner` — no listener |
| 1:45–2:45 | Evidence chain | `diagnose --proof`, `proxy-timeline` or replay JSONL |
| 2:45–3:30 | Unknown listener contrast | Brief show `unknown_localhost_proxy.json` — investigate, don't kill |
| 3:30–4:15 | Safe remediation | `proxy-disable --dry-run`, mention confirmation token |
| 4:15–4:45 | Analytics KPIs | `analytics-summary --audit-dir tests/fixtures/analytics/audit_sample --format markdown` |
| 4:45–5:00 | Close | Portfolio value — risk, audit, data analyst audiences |
| 4:15–5:00 | Business value | Report + dashboard; link to case studies and CI safety tests |

**Extra command (unknown listener — 30 sec):**

```powershell
python -m windows_network_toolkit proxy-writer-attribution --fixture tests/fixtures/enert/unknown_localhost_proxy.json
```

**Voiceover:**
> "When a listener exists but we can't prove who wrote the registry, confidence stays low and the tool blocks aggressive remediation. Correlation is not causation."

---

## Recording Checklist

- [ ] Terminal font size 14+ for readability
- [ ] Use fixture commands for cross-platform recording (no admin required)
- [ ] Highlight `limitations[]` in every JSON output
- [ ] Do not run destructive commands on camera without explicit dry-run
- [ ] Add lower-third: "Observation ≠ Proof"
- [ ] End card: link to README + `docs/portfolio-summary.md`
