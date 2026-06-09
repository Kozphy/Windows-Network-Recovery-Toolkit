# Timeline

| Time (UTC) | Event | Detail |
| --- | --- | --- |
| 2026-06-08T04:58:10Z | baseline_snapshot | ProxyEnable=0, ProxyServer empty |
| 2026-06-08T05:00:55Z | proxy_change_detected | ProxyEnable=1, ProxyServer=127.0.0.1:64394 |
| 2026-06-08T05:00:56Z | listener_observed | Port 64394 owned by node.exe (PID 12345) |
| 2026-06-08T05:01:02Z | sysmon_registry_write | Event ID 13 — ProxyServer value set (fixture) |
| 2026-06-08T05:01:10Z | policy_evaluated | OBSERVE — known dev tooling on allowlist |
| 2026-06-08T05:01:15Z | remediation_preview | proxy-disable preview generated (not executed) |
