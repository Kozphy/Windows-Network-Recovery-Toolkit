# Incident review (source notes)

## Impact

- Developer IDE session enabled loopback proxy; browsing may route through local Node listener
- No production outage in synthetic scenario; drift logged for audit

## Limitations

- Demo uses `tests/fixtures/proxy_incidents/cursor_known_proxy.json` — not a live endpoint
- Final causation requires Sysmon/Procmon on real hosts

## Follow-up actions

- Confirm with developer that proxy port is intentional
- Keep proxy-watch enabled; no autonomous disable
