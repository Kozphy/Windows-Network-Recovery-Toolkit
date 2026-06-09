# Security tooling walkthrough

## Evidence ladder

| Level | Source | Claim strength |
|-------|--------|----------------|
| Observation | WinINET read, listener | Weak |
| Correlation | Port aligns with ProxyServer | Candidate only |
| Proof | Sysmon E13 / Procmon | Writer attribution |
| Final causation | Multi-signal fusion | Highest in toolkit |

## Policy-as-code gates

`config/policies/strict_enterprise.yaml`:

- `block` — external proxy, destructive verbs
- `require_confirmation` — unknown localhost proxy
- `observe` — known dev tooling (still logged)

Validate: `python -m src policy-validate config/policies/strict_enterprise.yaml`

## Forensics commands (read-only)

```powershell
python -m src proxy-causation --fixture tests/fixtures/proxy_causation/scenario1_proven_writer_port_owner
python -m src proxy-forensics --fixture ...
python -m src incident-review --incident-id 001_proxy_drift_cursor_node
```

## Out of scope (by design)

- Autonomous kill / firewall reset
- Default telemetry exfiltration
- Unsigned RBAC headers as production auth
