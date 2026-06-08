# Demo video script

## 30-second version

1. Show `proxy-watch` detecting ProxyEnable `0 → 1` and ProxyServer `None → 127.0.0.1:<port>`.
2. Show **final causation** banner: Sysmon Event ID 13 registry writer + Details match.
3. Show `proxy-classify --latest` → `UNKNOWN_LOCAL_PROXY` or `KNOWN_CURSOR_PROXY`.
4. Show `proxy-policy --latest` → `ALERT` / `OBSERVE` (no auto-kill).
5. Show `proxy-timeline --fixture ... --format markdown` ordered events.
6. Open dashboard `/platform/proxy-events` evidence tree.

## 2-minute version

1. **Problem** — ping works, browser fails; WinINET drift to localhost proxy.
2. **Correlation vs causation** — listener on port ≠ registry writer.
3. **Fixture replay** (Linux-safe):
   ```bash
   python -m src proxy-timeline --fixture tests/fixtures/proxy_incidents/unknown_node_powershell_proxy.json --format markdown
   ```
4. **Final causation** — node.exe wrote ProxyServer; parent powershell.exe lineage.
5. **Classification** — neutral labels only (suspicious / unknown / possible MITM risk).
6. **Policy** — BLOCK_RECOMMENDED requires human review; preview-disable only.
7. **Dashboard** — incident card, timeline, evidence tree.
8. **Close** — read-only default; confirmation required for remediation.
