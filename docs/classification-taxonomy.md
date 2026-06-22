# Classification Taxonomy

**Engine:** `src/platform_core/classification/engine.py` · **Enum:** `src/platform_core/classification/models.py`

Each label includes definition, evidence requirements, proof tier guidance, policy action, and FP/FN risks.

---

## NO_PROXY

| Attribute | Detail |
|-----------|--------|
| **Definition** | Proxy disabled; no PAC URL |
| **Required evidence** | `ProxyEnable=0`, empty AutoConfigURL |
| **Optional** | WinHTTP direct confirmation |
| **Proof tier** | T1 |
| **Policy** | `ALLOW` observe |
| **Example** | Healthy direct endpoint |
| **False positive** | PAC bypass via group policy not read |
| **False negative** | Proxy via WPAD not captured |

---

## DEAD_PROXY_CONFIG

| Attribute | Detail |
|-----------|--------|
| **Definition** | WinINET points to localhost port with no listener |
| **Required evidence** | `ProxyEnable=1`, localhost `ProxyServer`, listener check failed |
| **Optional** | WinHTTP mismatch secondary; path contrast T2 |
| **Proof tier** | T1–T2 |
| **Policy** | `PREVIEW_ONLY` remediation |
| **Example** | Golden case 59081 |
| **False positive** | Transient listener race during probe |
| **False negative** | Non-localhost dead proxy misclassified as SUSPICIOUS |

---

## LOCAL_PROXY_ACTIVE

| Attribute | Detail |
|-----------|--------|
| **Definition** | Listener bound on configured localhost port |
| **Required evidence** | Matching port in netstat + config |
| **Optional** | Process name/path |
| **Proof tier** | T2 |
| **Policy** | `ALLOW` observe or `PREVIEW_ONLY` if change needed |
| **Example** | Active dev proxy on 8080 |
| **False positive** | Stale config with new listener on different port |
| **False negative** | IPv6 loopback listener missed |

---

## UNKNOWN_LOCAL_PROXY

| Attribute | Detail |
|-----------|--------|
| **Definition** | Active listener; process not in allowlist |
| **Required evidence** | Listener + PID without dev/security match |
| **Optional** | Parent process tree |
| **Proof tier** | T2 |
| **Policy** | `REQUIRE_HUMAN_REVIEW` |
| **Example** | `unknown_svc.exe` on 61526 |
| **False positive** | New legitimate tool not in heuristics |
| **False negative** | Known tool with renamed binary |

---

## KNOWN_DEV_PROXY

| Attribute | Detail |
|-----------|--------|
| **Definition** | Listener matches dev-tool heuristics (Node, Cursor, etc.) |
| **Required evidence** | Process/path allowlist match |
| **Optional** | Port correlation |
| **Proof tier** | T2 |
| **Policy** | `ALLOW` observe |
| **Example** | Cursor extension proxy |
| **False positive** | Malware mimicking dev binary name |
| **False negative** | Custom dev proxy not in list |

---

## KNOWN_SECURITY_TOOL

| Attribute | Detail |
|-----------|--------|
| **Definition** | Listener matches security product heuristics |
| **Required evidence** | Vendor/path match |
| **Proof tier** | T2 |
| **Policy** | `ALLOW` observe; coordinate with security team |
| **False positive** | Outdated heuristic list |
| **False negative** | New EDR proxy agent |

---

## SUSPICIOUS_PROXY

| Attribute | Detail |
|-----------|--------|
| **Definition** | External or non-localhost suspicious proxy config |
| **Required evidence** | Remote proxy server or anomalous config |
| **Proof tier** | T1–T2 |
| **Policy** | `REQUIRE_HUMAN_REVIEW` |
| **Example** | Unknown remote proxy in WinINET |
| **False positive** | Corporate forward proxy mis-tagged |
| **False negative** | Localhost tunnel to remote |

---

## POSSIBLE_MITM_RISK

| Attribute | Detail |
|-----------|--------|
| **Definition** | ≥2 independent MITM **indicators** (never confirmed MITM) |
| **Required evidence** | TLS mismatch + proxy/listener signals |
| **Proof tier** | T2–T3 |
| **Policy** | `REQUIRE_HUMAN_REVIEW`; no autonomous containment |
| **Example** | Browser TLS fail + unknown listener |
| **False positive** | Corporate SSL inspection |
| **False negative** | Single-indicator MITM |

---

## PAC_CONFIGURED

| Attribute | Detail |
|-----------|--------|
| **Definition** | AutoConfigURL set |
| **Required evidence** | Non-empty PAC URL in registry |
| **Proof tier** | T1 |
| **Policy** | `ALLOW` observe; validate PAC reachability separately |
| **Example** | `proxy_transitions/pac_added.json` |
| **False positive** | Stale PAC URL with direct override |
| **False negative** | WPAD-only configuration |

---

## WININET_WINHTTP_MISMATCH

| Attribute | Detail |
|-----------|--------|
| **Definition** | WinINET proxy path differs from WinHTTP |
| **Required evidence** | Both stacks read; paths differ |
| **Proof tier** | T1–T2 |
| **Policy** | `PREVIEW_ONLY` alignment preview |
| **Example** | WinINET proxy, WinHTTP direct |
| **False positive** | Intentional split-stack design |
| **False negative** | Both proxied via different hosts |

---

## REVERTER_SUSPECTED

| Attribute | Detail |
|-----------|--------|
| **Definition** | Watch history shows repeated proxy reappearance |
| **Required evidence** | Timeline with disable→re-enable pattern |
| **Optional** | Parent PID on writer |
| **Proof tier** | T2–T4 |
| **Policy** | `REQUIRE_HUMAN_REVIEW` |
| **Example** | Flapping loop JSONL |
| **False positive** | User manually re-enabling |
| **False negative** | Reverter outside watch window |

---

## TLS_PATH_MISMATCH

| Attribute | Detail |
|-----------|--------|
| **Definition** | Browser and curl/system TLS paths diverge (when primary) |
| **Required evidence** | `tls-proof` contrast results |
| **Proof tier** | T3 |
| **Policy** | `PREVIEW_ONLY`; escalate if persistent |
| **Example** | Browser fails, curl succeeds |
| **False positive** | Different SNI or cert store |
| **False negative** | Both fail equally |

*Note: Often surfaced as secondary signal under `POSSIBLE_MITM_RISK` or dedicated TLS classifier output.*

---

## ERROR_INSUFFICIENT_DATA

| Attribute | Detail |
|-----------|--------|
| **Definition** | Missing proxy state or permission denied |
| **Required evidence** | Collector failure or empty state |
| **Proof tier** | T0 |
| **Policy** | `BLOCK` remediation; collect more evidence |
| **Example** | Insufficient permissions to inspect process owner |
| **False positive** | Transient read failure |
| **False negative** | Partial state interpreted as complete |

---

## Tests

```powershell
pytest -q tests/platform_core/classification/test_classification_matrix.py
pytest -q tests/evaluation/test_scenario_matrix_15.py
```

*Legacy:* [classification-model.md](classification-model.md)
