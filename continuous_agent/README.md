# Continuous Monitoring Agent

This component runs the repository's bounded verification workflow continuously without requiring prompts.

## Safety model

- Read-only by default.
- Executes only checks explicitly listed in a trusted local configuration.
- Uses `shell=False`; arbitrary command strings are not accepted.
- Never performs remediation.
- Writes append-only JSONL observations and escalation records.
- Alerts only on state changes by default to avoid notification storms.
- A failed check becomes evidence; it does not terminate the long-running process.

## Run once

```powershell
python continuous_agent/agent.py --config continuous_agent/config.example.json --once
```

## Run continuously

```powershell
python continuous_agent/agent.py --config continuous_agent/config.example.json
```

The minimum interval is 10 seconds. The example configuration uses five minutes.

## Start automatically on Windows

Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./continuous_agent/install_windows_service.ps1
Start-ScheduledTask -TaskName WNRTContinuousAgent
```

The installer uses Windows Task Scheduler with an at-startup trigger, restart policy, limited run level, and single-instance behavior. It does not misrepresent plain Python as a native Windows Service. A future production packaging option is WinSW or a signed native service wrapper.

## Evidence outputs

- `artifacts/continuous-agent-state.json`: last known fingerprints and statuses.
- `artifacts/continuous-agent-audit.jsonl`: every observation cycle.
- `artifacts/continuous-agent-alerts.jsonl`: state-change escalations requiring review.
- `artifacts/continuous-harness-results.jsonl`: bounded harness verification evidence.

## Production hardening

1. Copy the example config and restrict write permissions.
2. Use absolute paths when installed outside the repository checkout.
3. Run under a dedicated low-privilege account rather than SYSTEM where practical.
4. Sign release artifacts and pin the Python/runtime distribution.
5. Forward JSONL evidence through OpenTelemetry or a controlled log shipper.
6. Add an OPA client before permitting any action beyond observation.
7. Keep registry changes, service restarts, proxy modifications, and other privileged operations behind explicit human approval.
