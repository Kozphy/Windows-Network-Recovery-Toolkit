# Timeline

| Time (UTC) | Event | Detail |
| --- | --- | --- |
| 2026-06-10T09:15:00Z | proxy_change_detected | External-looking proxy enabled (fixture) |
| 2026-06-10T09:16:00Z | remediation_preview | proxy-disable preview_id=prev-demo-003 |
| 2026-06-10T09:16:30Z | remediation_execute | dry_run=false blocked in CI; success in demo fixture |
| 2026-06-10T09:18:00Z | proxy_change_detected | Proxy re-enabled — stickiness check failed |
| 2026-06-10T09:18:05Z | signal_stickiness_failed | remediation_stickiness_failed recorded |
| 2026-06-10T09:18:10Z | policy_evaluated | require_confirmation — active reverter suspected |
