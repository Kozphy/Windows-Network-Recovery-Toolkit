# Case study: Chromium `ERR_TIMED_OUT` + localhost proxy

## Symptoms

- Chrome / Edge show `ERR_TIMED_OUT`
- `curl -I https://www.google.com` works
- `Test-NetConnection` to port 443 succeeds
- `ProxyEnable = 1`, `ProxyServer = 127.0.0.1:<dynamic port>`
- A local process (`node.exe`, dev proxy, MCP bridge, VPN helper) may LISTEN on that port

## Diagnosis framing (neutral wording)

Browser traffic may be routed through an **unexpected localhost proxy**. System-level probes can stay healthy while Chromium honors WinINET proxy settings pointing at loopback.

## Safe operator response

1. `python -m src proxy-status` (see mode + localhost port hints)
2. `python -m src proxy-owner` (listener PID + parent tooling)
3. `python -m src proxy-monitor` (detect re-enablement/regression loops)
4. `python -m src proxy-disable --dry-run`, then deliberate apply with typed confirmation
5. `python -m src diagnose-live` for ranked hypotheses plus JSON artifacts under `reports/`

## Limits

Removing proxy keys does **not** remove the updater process; monitor for recurrence and trace Task Scheduler/services if needed.
