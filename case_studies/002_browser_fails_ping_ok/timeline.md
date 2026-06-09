# Timeline

| Time (UTC) | Event | Detail |
| --- | --- | --- |
| 2026-06-09T14:00:00Z | user_report | Browser cannot load https://example.com |
| 2026-06-09T14:00:05Z | probe_ping | 8.8.8.8 reachable (4/4 replies) |
| 2026-06-09T14:00:06Z | probe_dns | DNS resolution OK for example.com |
| 2026-06-09T14:00:08Z | probe_browser_path | HTTPS via WinINET failed (fixture) |
| 2026-06-09T14:00:10Z | proxy_state_read | ProxyEnable=1, stale loopback port |
| 2026-06-09T14:00:12Z | hypothesis_ranked | Leading: stale localhost proxy |
| 2026-06-09T14:00:20Z | policy_evaluated | PREVIEW — repair preview allowed, execute gated |
