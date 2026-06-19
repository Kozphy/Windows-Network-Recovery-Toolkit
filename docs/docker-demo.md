# Reviewer Docker Demo (Option C)

Minimal API stack for hiring panels — **read-only**, fixture-backed, no Postgres/Prometheus/Grafana.

Full production-shaped stack: [production_deployment.md](production_deployment.md) and root `docker-compose.yml`.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Ports `8000` available on localhost

---

## Start demo stack

```bash
docker compose -f docker-compose.demo.yml up --build
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","mode":"demo"}
```

---

## Sample API calls

```bash
curl -s http://127.0.0.1:8000/trisk/health
curl -s http://127.0.0.1:8000/incidents
curl -s http://127.0.0.1:8000/reports/executive
```

---

## Local CLI (no Docker)

```powershell
python -m windows_network_toolkit reviewer-demo --mode mixed
python -m windows_network_toolkit fleet-simulate --endpoints 100 --seed 42 --out examples/fleet/audit_sample
```

Makefile shortcuts: `make demo-up`, `make demo-health`, `make demo-report`.

---

## Fixture directory

Read-only mount: `fixtures/proxy/` — dead proxy, WinINET/WinHTTP mismatch, toggle loop, remote proxy.

Writable demo artifacts: `demo-output/` (audit, reports, timelines).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8000 in use | Stop other API or change host port in compose file |
| Health check fails | Wait for `start_period`; check container logs |
| `/trisk/*` empty | `PLATFORM_FIXTURE_MODE=1` uses bundled fixtures |

---

## Non-claims

This demo stack is a **portfolio prototype** for technology risk evidence and endpoint reliability analytics. It is **not** EDR, not malware detection, not autonomous remediation, and not a formal audit product. `DEMO_MODE=true` forces dry-run and blocks live destructive execute paths.
