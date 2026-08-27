# Purple Team Safety Model

## Gates (all required for non-dry-run)

1. `safe_for_local_execution=true`
2. Cleanup/rollback declared
3. Preconditions declared
4. No remote target
5. No production target
6. Supported environment (`lab` / `ci` / `fixture`)
7. Authorized flag or dry-run
8. Fixture-backed simulation path

## Dry-run

```bash
python -m src.purple_team validate proxy-drift-001
```

Shows actions, expected evidence, rollback, detection, risk, verification — **zero host mutation**.

## Authorization token

`PURPLE_TEAM_LAB_ONLY` — lab/fixture authorization only. Does not unlock blocked live actions in `windows_network_toolkit.safety` (`KILL_PROXY_PROCESS`, firewall reset, adapter disable, WinHTTP modify).

## Non-goals

No malware, stealth, credential theft, persistence, destructive exploits, or MITM.
