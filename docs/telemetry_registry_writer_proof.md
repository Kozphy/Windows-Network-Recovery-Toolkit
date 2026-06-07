# Registry Writer Telemetry Proof Layer

This document describes the **Telemetry Evidence Upgrade v1** package under `telemetry/`. It strengthens proxy attribution by ingesting registry-write telemetry (Sysmon, Windows Event Log, optional ETW fixtures) and fusing it with existing listener evidence.

---

## Purpose

Proxy drift diagnosis often observes:

1. WinINET proxy enabled (`ProxyEnable`)
2. `ProxyServer` pointing at `127.0.0.1:<port>`
3. A local process listening on that port

That chain shows **correlation**, not **registry-writer proof**. A process can listen on a port without having written the registry value, and a registry write can precede a different listener owner.

The telemetry layer answers a narrower question:

> **Which process (if any) appears in registry-write telemetry for the proxy keys around the change time?**

---

## Why listener correlation is not proof

Listener attribution uses netstat/process metadata. It is useful candidate evidence for operations and risk scoring, but it does not demonstrate a registry write. Stronger claims require telemetry such as:

- **Sysmon Event ID 13** — registry value set
- **Security Event ID 4657** — registry auditing (when enabled)
- **Procmon / ETW exports** — operator-supplied traces

See [ADR-004-heuristic-attribution-is-not-proof.md](adr/ADR-004-heuristic-attribution-is-not-proof.md).

---

## Sysmon / Event Log / ETW role

| Source | Role in v1 |
|--------|------------|
| **Sysmon EID 13** | Primary fixture parser; extracts `TargetObject`, `Details`, `Image`, `ProcessId` |
| **Windows Event Log** | Fixture-first abstraction; live query is optional and best-effort |
| **ETW** | Optional adapter; fixture parser only in tests — no live session required |

Target registry values:

- `ProxyEnable`
- `ProxyServer`
- `AutoConfigURL`
- `ProxyOverride`

Under `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\`.

---

## Evidence levels

| Level | Meaning |
|-------|---------|
| `NO_TELEMETRY` | No telemetry rows supplied |
| `NO_RELEVANT_REGISTRY_WRITES` | Telemetry present but no proxy-key writes in window |
| `REGISTRY_WRITER_OBSERVED` | Relevant registry writes observed |
| `WRITER_AND_LISTENER_MATCH` | Writer identity aligns with listener owner (still not intent proof) |
| `CONFLICTING_EVIDENCE` | Writer and listener disagree — unresolved attribution |
| `INCONCLUSIVE` | Relevant writes lack sufficient process identity fields |

`confidence_rank` is ordinal (`none` → `high`), not a calibrated probability.

---

## Safety boundaries

This layer is **diagnostic only**:

- No auto-remediation
- No process kill
- No certificate deletion
- No firewall reset
- No adapter disable
- No registry mutation

Outputs are evidence summaries, audit rows, and policy inputs only. Repair paths still require explicit operator confirmation and existing policy gates.

---

## Example input (Sysmon fixture)

```json
{
  "EventID": 13,
  "UtcTime": "2026-01-15T12:00:06.000Z",
  "TargetObject": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyServer",
  "Details": "127.0.0.1:63722",
  "Image": "C:\\Program Files\\nodejs\\node.exe",
  "ProcessId": 21712
}
```

Fixtures live under `tests/fixtures/telemetry/`.

---

## Example output (fusion)

```json
{
  "evidence_level": "WRITER_AND_LISTENER_MATCH",
  "confidence_rank": "high",
  "candidate_writers": [
    {
      "process_id": 21712,
      "process_name": "node.exe",
      "process_path": "C:\\Program Files\\nodejs\\node.exe"
    }
  ],
  "listener_match": {
    "matched": true,
    "listener": { "process_id": 21712, "process_name": "node.exe" },
    "writers": [{ "process_id": 21712, "process_name": "node.exe" }]
  },
  "limitations": [
    "WRITER_AND_LISTENER_MATCH means the same process appears to have written the proxy key and owned the listener port; this still does not prove intent."
  ],
  "recommended_next_steps": [
    "Preserve telemetry exports and correlate with proxy drift timeline."
  ]
}
```

---

## CLI

```powershell
python -m telemetry.cli parse-sysmon-fixture tests/fixtures/telemetry/sysmon_event13_proxy_enable_node.json --pretty
python -m telemetry.cli fuse-registry-writer-evidence `
  --events tests/fixtures/telemetry/sysmon_event13_proxy_server_node.json `
  --proxy-change-time 2026-01-15T12:00:10Z `
  --listener tests/fixtures/telemetry/listener_node.json `
  --pretty
python -m telemetry.cli explain evidence.json --pretty
```

Optional integration with legacy proxy guard scan:

```powershell
python -m proxy_guard scan `
  --telemetry-events tests/fixtures/telemetry/sysmon_event13_proxy_server_node.json `
  --proxy-change-time 2026-01-15T12:00:10Z
```

---

## Audit

Fusion summaries append to `logs/registry_writer_evidence.jsonl` (gitignored). Rows exclude full raw events unless `--include-raw` is set on the telemetry CLI fuse command.

---

## Policy impact

Telemetry fusion can **upgrade evidence quality** for previews and human review. It **cannot**:

- Prove malicious intent
- Bypass typed confirmation
- Enable destructive actions blocked by policy

Policy remains orthogonal: **ALLOW / PREVIEW / BLOCK** gates are unchanged.

---

## Limitations

- Fixture parsers tolerate missing fields with `parse_warnings`; incomplete rows may yield `INCONCLUSIVE`.
- Live Event Log and ETW ingestion require Windows, privileges, and operator configuration.
- Multiple writers in one window may produce `CONFLICTING_EVIDENCE` even when one writer matches the listener.
- Replay uses supplied telemetry; it does not re-probe the host.

See also [epistemic_model.md](epistemic_model.md) and [safety_model.md](safety_model.md).
