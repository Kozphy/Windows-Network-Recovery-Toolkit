# Productization Map

This map ties dashboard-visible product claims to backend contracts. The implementation is intentionally conservative: when evidence is missing, the API says what is missing and recommends the next test instead of claiming root cause.

| Frontend Element | Backend API | Schema | Evidence Source | Policy/Audit Requirement |
| --- | --- | --- | --- | --- |
| Backend health | `GET /platform/health` | `HealthResponse` | backend process flags, JSONL path | expose local-first mode, safe mode, and dry-run default |
| Endpoint fleet view | `GET /platform/endpoints` | `EndpointSummary` | endpoint heartbeat JSONL, diagnosis JSONL, LKG JSONL | no raw hostname; join only stored evidence |
| Endpoint detail | `GET /platform/endpoints/{endpoint_id}` | `EndpointSummary` | same as fleet view | 404 when no stored or synthesized endpoint exists |
| Healthy / degraded / drift proxy badges | `GET /platform/endpoints` and `GET /platform/diagnosis/latest` | `EndpointSummary`, `DiagnosisResult` | risk score from typed observations | diagnosis run must append audit row |
| DNS stability | `POST /platform/diagnosis/run` | `ProbeResult(name=dns_probe)` | `socket.getaddrinfo` placeholder adapter | observation-level evidence unless corroborated |
| TCP `:443` status | `POST /platform/diagnosis/run` | `ProbeResult(name=tcp_443_probe)` | bounded `socket.create_connection` | observation-level evidence |
| HTTPS probe status | `POST /platform/diagnosis/run` | `ProbeResult(name=https_probe)` | Python TLS handshake placeholder | observation-level evidence |
| Proxy / WinINET drift | `POST /platform/diagnosis/run` | `ProbeResult(name=wininet_proxy_state)` | existing proxy signal collector | inference only unless registry writer telemetry exists |
| WinHTTP parity check | `POST /platform/diagnosis/run` | `ProbeResult(name=winhttp_proxy_state)` | `netsh winhttp show proxy` read-only adapter | observation-level evidence |
| Localhost proxy listener hint | `POST /platform/diagnosis/run` | `ProbeResult(name=localhost_proxy_listener)` | existing proxy port attribution | candidate actor only; never called writer proof |
| Git/npm proxy stack check | `POST /platform/diagnosis/run` | `ProbeResult(name=git_npm_proxy_config)` | read-only `git config` / `npm config` | warning/unknown when tools unavailable |
| LKG availability | `GET /platform/lkg/{endpoint_id}` | LKG snapshot row | `platform_data/lkg_snapshots.jsonl` | append audit on snapshot creation |
| Detect → Attribute → Decide → Rollback → Audit pipeline | diagnosis, attribution, remediation, rollback, audit APIs | `DiagnosisResult`, attribution payloads, remediation responses | stored observations plus optional proof telemetry | policy decision and audit event required at each step |
| Remediation preview | `POST /platform/remediation/preview` | legacy preview + contract fields | stored `FailureEvent`, remediation registry | preview-only response and append audit event |
| Remediation execute | `POST /platform/remediation/execute` | legacy execution + contract fields | persisted preview and policy registry | `dry_run=true` by default; high-risk blocked |
| Rollback preview | `POST /platform/rollback/preview` | rollback preview dict | LKG snapshot JSONL | preview only; explicit targeted fields only |
| Append-only JSONL audit tail | `GET /platform/audit/tail` | `PlatformAuditEvent` where available | `platform_data/audit.jsonl` | product rows include hash and replay reference |
| Replay diagnosis | `GET /platform/replay/{run_id}` | replay envelope | stored diagnosis observations | must not reprobe live machine |
| Agentic next step | `POST /platform/agent/next-step` | `AgentNextStepResponse` | stored diagnosis evidence | suggest/explain only; no repair action |

## Evidence Language

Netstat tells who is listening on a port. Sysmon or Procmon-style registry telemetry tells who wrote the registry. These are different.

The platform uses these labels:

- `observation`: a probe read a current state or stored row
- `inference`: the system correlated facts into a hypothesis
- `proof`: a proof telemetry source directly supports the claim

For intermittent proxy drift, a localhost listener can identify a `candidate_actor`. It does not prove that the same process changed `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`.

## Product Control Boundary

The platform is valuable because it turns endpoint confusion into a repeatable workflow:

1. Read evidence locally.
2. Separate facts from hypotheses.
3. Apply policy gates.
4. Preview safe actions.
5. Append audit records.
6. Replay without re-probing.

The defensible platform asset is the evidence and policy contract, not a flat repair script.

