# Proxy Writer Attribution

The Proxy Change Attribution System answers a narrow question: which process has
evidence of writing WinINET proxy values under:

`HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`

Tracked values:

- `ProxyEnable`
- `ProxyServer`
- `AutoConfigURL`
- `ProxyOverride`
- `AutoDetect`

## Evidence Levels

| Level | Meaning | Decision impact |
| --- | --- | --- |
| `OBSERVED_STATE` | Current WinINET tuple only. | Diagnose only. |
| `STATE_CHANGE` | The tuple changed between snapshots. | Preview only; writer is unknown. |
| `CORRELATED_PROCESS` | A process is listening on the configured localhost proxy port. | Candidate actor only. |
| `WRITER_PROOF` | Sysmon, Security Event Log, Procmon, or ETW-style telemetry shows a registry write. | Strong local evidence, still review source limitations. |

Netstat tells who is listening. Sysmon/Procmon tells who wrote the registry. These are different.

## Architecture

Inputs:

- WinINET proxy snapshots from local registry reads.
- Localhost listener/process correlation from netstat/tasklist/CIM.
- Sysmon Event ID 13 registry `SetValue` telemetry when available.
- Windows Security Event ID 4657 registry auditing when configured.
- Optional Procmon CSV exports.
- Persistence and trusted-root certificate indicators.
- Safe DNS, TCP 443, direct HTTPS, and proxy HTTPS connectivity probes.

Processing:

1. Observe current proxy tuple.
2. Detect tuple changes between polls.
3. Correlate configured localhost proxy ports to listener candidates.
4. Query registry-write telemetry around the change window.
5. Classify risk and apply conservative policy gates.
6. Append one JSON line to `logs/proxy_writer_audit.jsonl`.

Outputs:

- `ProxyAttributionEvent` JSONL rows.
- JSON and Markdown writer reports.
- Per-event explanations for audit review.

## Commands

```powershell
python -m proxy_guard watch-writer
python -m proxy_guard writer-report --json
python -m proxy_guard writer-report --markdown
python -m proxy_guard import-procmon path\to\procmon.csv
python -m proxy_guard explain-event <event_id>
```

Useful options:

```powershell
python -m proxy_guard watch-writer --interval 3 --since-seconds 180
python -m proxy_guard watch-writer --procmon-csv path\to\procmon.csv
python -m proxy_guard watch-writer --once
```

`--once` prints a single observed-state snapshot and does not append a change event.

## Sysmon Requirements

Writer proof from Sysmon requires:

- Sysmon installed and running.
- The `Microsoft-Windows-Sysmon/Operational` log readable by the user.
- Event ID 13 registry value set telemetry enabled for the WinINET proxy path.

If Sysmon is not installed or the log is unavailable, the system reports:

`writer proof unavailable; enable Sysmon registry telemetry or import Procmon trace.`

That limitation keeps the event at `STATE_CHANGE` or `CORRELATED_PROCESS`; it does not become writer proof.

## Procmon Import

`import-procmon` parses CSV exports for successful `RegSetValue` rows targeting the monitored
WinINET proxy values. The import is read-only and append-only. Preserve the original Procmon trace
when audit chain of custody matters.

## Classifications

- `MANUAL_USER_CHANGE`
- `KNOWN_BROWSER_OR_SYSTEM_COMPONENT`
- `KNOWN_VPN_OR_SECURITY_TOOL`
- `KNOWN_DEV_PROXY`
- `UNKNOWN_PROCESS_CHANGED_PROXY`
- `PROXY_CHANGED_WITH_NO_WRITER_PROOF`
- `POSSIBLE_MITM_RISK`
- `CONNECTIVITY_REGRESSED_AFTER_PROXY_CHANGE`

## Policy Gates

- Writer proof unavailable: `PREVIEW`.
- Known writer: `ALLOW` safe restore preview only.
- Unknown writer plus localhost proxy plus suspicious certificate or persistence signal: `BLOCK`.
- Connectivity regression after a proxy change: investigate before restore.

The system never kills processes, deletes certificates, resets firewall, disables adapters, or performs
blind registry resets. Registry restore must be targeted and explicitly confirmed through a separate
remediation path.

## Audit Interpretation

Use audit language:

- Observation: registry values and probe outputs.
- Inference: risk classification from observations.
- Proof: registry-write telemetry from Sysmon, Security log, Procmon, or ETW-style sources.

Reasonable assurance is possible when telemetry is present and time windows align. Absolute certainty is
not claimed because logs can be missing, delayed, rotated, or tampered with on compromised endpoints.

