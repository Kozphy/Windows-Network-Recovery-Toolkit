# Proof vs observation

This platform separates **what we observed** from **what we tested** and **what we can conclude**.

---

## Definitions

| Term | Meaning |
|------|---------|
| **Observation** | Read-only facts: registry values, netstat rows, WinHTTP settings |
| **Hypothesis** | Testable explanation for symptoms (e.g. dead WinINET proxy) |
| **Proof attempt** | Named check with pass/fail/supported status |
| **Conclusion** | Whether evidence supports the hypothesis, with confidence and limitations |

**Observation alone never implies remediation approval.**

---

## Proof envelope

Implemented in `windows_network_toolkit/proof.py`, wrapping `src/platform_core/proof/engine.py`.

```json
{
  "observation": {
    "wininet_proxy": "127.0.0.1:59081",
    "winhttp_direct": true,
    "localhost_listener": false
  },
  "hypothesis": "Browser failure is likely caused by dead WinINET localhost proxy.",
  "proof_attempts": [
    {
      "name": "localhost_listener_check",
      "status": "failed",
      "meaning": "No process is listening on the configured proxy port."
    },
    {
      "name": "wininet_winhttp_comparison",
      "status": "supported",
      "meaning": "Browser proxy path differs from WinHTTP direct path."
    }
  ],
  "conclusion": {"status": "supported", "confidence": 0.92},
  "limitations": [
    "This does not prove malware.",
    "This does not prove MITM."
  ]
}
```

---

## Proof attempts

| Name | Purpose |
|------|---------|
| `localhost_listener_check` | netstat / listener probe on configured port |
| `wininet_winhttp_comparison` | Contrast WinINET proxy path vs WinHTTP direct |
| `direct_connectivity_check` | Optional HTTP/TCP without proxy |
| `proxied_connectivity_check` | Optional HTTP/TCP via configured proxy |
| `dns_check` | Optional DNS resolution probe |

---

## CLI

```powershell
python -m windows_network_toolkit diagnose --proof
python -m windows_network_toolkit diagnose --proof --fixture tests/fixtures/enert/dead_proxy_59081.json
python -m windows_network_toolkit diagnose --proof --url https://example.com
```

---

## What proof does NOT claim

- **Malware identification** — requires EDR/forensics
- **Registry writer identity** — requires Sysmon E13 or equivalent
- **Confirmed MITM** — `POSSIBLE_MITM_RISK` requires multiple indicators; proof envelope always lists limitations

---

## Relationship to evidence tiers

Platform evidence tiers (`OBSERVED_ONLY` → `FINAL_CAUSATION`) govern **attribution strength**.  
The proof envelope governs **hypothesis support for a specific symptom**.

Both must align before policy allows remediation. See [evidence_model.md](evidence_model.md) and [policy_model.md](policy_model.md).

---

## Tests

```powershell
pytest -q tests/windows_network_toolkit/test_diagnose_proof.py
```
