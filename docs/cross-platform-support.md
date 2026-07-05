# Cross-platform evidence support

**Status:** Honest PARTIAL Linux/macOS foundation — no fake WinINET/WinHTTP parity.

**Related:** [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) · [evidence-model.md](evidence-model.md) · [agent-deployment.md](agent-deployment.md)

---

## Platform support levels

| OS | Level | Collector | Live remediation |
|----|-------|-----------|------------------|
| Windows | `FULL` | `windows_network_diagnostics_v1` | Policy-gated (existing toolkit) |
| Linux | `PARTIAL` | `linux_network_diagnostics_v1` | **Not supported** |
| macOS | `PARTIAL` | `darwin_network_diagnostics_v1` | **Not supported** |
| Unknown | `NOT_SUPPORTED` | `unsupported_platform_v1` | **Not supported** |

Factory: `src/platform_core/evidence_collection/factory.py`

```python
from src.platform_core.evidence_collection import collect_endpoint_evidence

bundle = collect_endpoint_evidence("linux")  # or None for host auto-detect
```

---

## What each OS collects (read-only)

### Windows (`FULL`)

Delegates to `platform_core/network_diagnostics/windows.py`:

- WinINET / WinHTTP proxy observations
- Environment proxy variables
- DNS / hostname
- Existing registry and netstat correlation paths elsewhere in the toolkit

**Does not claim:** malware detection, MITM proof, or autonomous safe repair.

### Linux (`PARTIAL`)

Delegates to `platform_core/network_diagnostics/linux.py`:

| Signal class | Source |
|--------------|--------|
| Environment proxy | `http_proxy`, `HTTPS_PROXY`, etc. |
| System proxy hints | `src/proxy_guard/linux_proxy_snapshot.py` (gsettings, `/etc/environment`, NetworkManager, apt when available) |
| Listening ports | `ss -tln` or `netstat -an` summary |
| DNS / hostname / resolv.conf | Read-only filesystem and socket probes |

**Explicitly not collected:** WinINET, WinHTTP, Windows registry writers.

### macOS (`PARTIAL`)

Delegates to `platform_core/network_diagnostics/darwin.py`:

| Signal class | Source |
|--------------|--------|
| Environment proxy | Standard `*_proxy` env vars |
| System proxy hints | `networksetup -getwebproxy` / `-getsecurewebproxy` when safely available |
| Listening ports | Same POSIX listener summary as Linux |
| DNS / hostname | Socket probes |

**Explicitly not collected:** WinINET, WinHTTP, Windows registry concepts.

When `networksetup` is missing or fails, observations record `networksetup_available: false` — the collector does **not** crash.

---

## Limitations doctrine

Every non-Windows bundle **must** include non-empty `limitations[]`:

- Observation is not proof
- No WinINET/WinHTTP parity on Linux/macOS
- Listener summary is not process attribution
- Classification is not accusation

Normalization helpers: `src/platform_core/evidence_collection/normalize.py`

```python
from src.platform_core.evidence_collection.normalize import (
    normalize_evidence_bundle,
    assert_honest_platform_labels,
)
```

---

## Module map

```text
src/platform_core/evidence_collection/
  factory.py          # get_endpoint_evidence_collector()
  windows.py          # FULL — delegates to network_diagnostics.windows
  linux.py            # PARTIAL — delegates to network_diagnostics.linux
  darwin.py           # PARTIAL — delegates to network_diagnostics.darwin
  unsupported.py      # NOT_SUPPORTED
  normalize.py        # cross-platform bundle normalization

platform_core/network_diagnostics/
  windows.py          # WinINET/WinHTTP path
  linux.py            # env + linux_proxy_snapshot + listeners
  darwin.py           # env + networksetup + listeners
  listeners.py        # ss/netstat listener summary (POSIX)
```

---

## Fixtures and tests

| Path | Purpose |
|------|---------|
| `tests/fixtures/cross_platform/windows_evidence.json` | FULL Windows fixture |
| `tests/fixtures/cross_platform/linux_evidence.json` | PARTIAL Linux fixture |
| `tests/fixtures/cross_platform/darwin_evidence.json` | PARTIAL macOS fixture |
| `tests/platform_core/evidence_collection/test_platform_support.py` | Factory + support levels |
| `tests/platform_core/evidence_collection/test_normalization.py` | Fixture normalization |
| `tests/platform_core/evidence_collection/test_linux_darwin_collectors.py` | Collector behavior |

```powershell
pytest -q tests/platform_core/evidence_collection/
```

---

## Explicit non-claims

| Claim | Supported? |
|-------|------------|
| Windows proxy observation tier | **Yes** (`FULL`) |
| Linux/macOS env + proxy hints + listener summary | **Yes** (`PARTIAL`) |
| Linux/macOS WinINET/WinHTTP/registry parity | **No** |
| Cross-platform live remediation | **No** (Windows policy-gated only) |
| Malware / MITM / compromise detection | **No** |

Do not label Linux/macOS classifications as equivalent proof tiers to Windows registry-writer attribution.
