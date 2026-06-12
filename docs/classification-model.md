# Classification model

The classification engine maps WinINET/WinHTTP/proxy listener observations into **12 primary labels**, optional **secondary signals**, and a structured `ClassificationResult` with confidence 0–1.

**Canonical engine:** `src/platform_core/classification/engine.py`  
**Facade:** `windows_network_toolkit/proxy_classification.py`

---

## Primary classifications

| Label | Meaning |
|-------|---------|
| `NO_PROXY` | Proxy disabled, no PAC |
| `DEAD_PROXY_CONFIG` | Localhost proxy configured but no listener |
| `LOCAL_PROXY_ACTIVE` | Listener bound on configured localhost port |
| `UNKNOWN_LOCAL_PROXY` | Active listener, unknown process |
| `KNOWN_DEV_PROXY` | Active listener matches dev-tool heuristics |
| `KNOWN_SECURITY_TOOL` | Active listener matches security-tool heuristics |
| `SUSPICIOUS_PROXY` | External or suspicious proxy configuration |
| `POSSIBLE_MITM_RISK` | ≥2 independent MITM indicators (never "confirmed MITM") |
| `PAC_CONFIGURED` | AutoConfigURL set |
| `WININET_WINHTTP_MISMATCH` | WinINET proxy path differs from WinHTTP (primary when no dead listener) |
| `REVERTER_SUSPECTED` | Watch history shows repeated proxy reappearance |
| `ERROR_INSUFFICIENT_DATA` | Missing proxy state; confidence ≤ 0.3 |

---

## Secondary signals

Secondary signals annotate the primary label — they do not replace it.

Examples:

- `WININET_WINHTTP_MISMATCH`
- `DEAD_LOCALHOST_PORT`
- `LOCALHOST_PROXY`
- `PAC_PRESENT`
- `REGISTRY_REWRITE_OBSERVED`
- `REPEATED_PROXY_REAPPEARANCE`
- `WRITER_LISTENER_MISMATCH`

Full enum: `src/platform_core/classification/models.py`

---

## ClassificationResult schema

```json
{
  "primary_classification": "DEAD_PROXY_CONFIG",
  "secondary_signals": ["WININET_WINHTTP_MISMATCH", "DEAD_LOCALHOST_PORT"],
  "severity": "medium",
  "confidence": 0.92,
  "reasoning": "ProxyServer references localhost:59081 but no listener is bound.",
  "evidence": ["localhost_port=59081", "listener_found=false"],
  "recommended_next_actions": ["Run diagnose --proof", "Preview proxy-disable"],
  "limitations": ["Does not prove malware or MITM."]
}
```

**Severity:** `info` · `low` · `medium` · `high`  
**Confidence:** float 0.0–1.0 (ordinal, not calibrated probability)

---

## Rule priority (summary)

1. Missing state → `ERROR_INSUFFICIENT_DATA`
2. `ProxyEnable=0` and no PAC → `NO_PROXY`
3. PAC URL set → `PAC_CONFIGURED` (unless dead localhost overrides)
4. Localhost port + no listener → `DEAD_PROXY_CONFIG` (up to ~0.92 with listener check)
5. Active listener → dev/security/unknown heuristics
6. WinINET enabled + WinHTTP direct → secondary or primary `WININET_WINHTTP_MISMATCH`
7. `POSSIBLE_MITM_RISK` only with ≥2 independent indicators
8. Watch history → `REVERTER_SUSPECTED`

---

## CLI usage

```powershell
python -m windows_network_toolkit proxy-status
python -m windows_network_toolkit proxy-status --fixture tests/fixtures/enert/dead_proxy_59081.json
```

`proxy-status` includes both:

- `classification` — primary label string (backward compatible)
- `classification_result` — full object

---

## Golden path: 59081

```
ProxyEnable=1, ProxyServer=127.0.0.1:59081, WinHTTP=direct, listener=false
→ DEAD_PROXY_CONFIG + WININET_WINHTTP_MISMATCH
```

Case study: [case-studies/dead-localhost-proxy.md](case-studies/dead-localhost-proxy.md)

---

## Tests

```powershell
pytest -q tests/platform_core/classification/test_classification_matrix.py
```
