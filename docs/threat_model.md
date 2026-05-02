# Threat model (local prototype scope)

This repository targets **portfolio / lab** workloads. Treat the following as design constraints:

| Asset | Risk | Mitigation |
| --- | --- | --- |
| Operator consoles | Cross-site scripting / confused deputy | localhost-only demos, RBAC simulation headers (`X-Operator-*`) |
| JSONL disks | Tampering between preview/execute | Correlate previews + executions + audits; rerun replay |
| Process attribution | False accusations | Confidence ladder capped at heuristic unless Sysmon/EventLog wired |
| API abuse | Replay attacks on execute | Confirmation phrases + SAFE_MODE gates + registry allowlisting |
| Sensitive telemetry | Disclosure of identities | Stable hashes (`endpoint_id_hash`), redaction helpers in `privacy.py` |

Explicit **non-controls**:

- Headers are unsigned—assume attacker with local access can forge them.
- No HSM-backed audit chain in this demo.

High-risk actions (`firewall_reset`, `adapter_disable`, arbitrary shell) remain **manual-only or forbidden** in the registry.
