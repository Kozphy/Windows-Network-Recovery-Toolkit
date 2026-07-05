# Demo commands reference (fixture-safe)

Extended command catalog moved from the root README. Works on any OS with fixtures — **no live registry changes** required.

## Prerequisites

```powershell
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
```

Shorter golden path: [demo_5_min.md](demo_5_min.md) · `make demo`

---

## Golden path (3-minute panel demo)

```powershell
python -m windows_network_toolkit proxy-status --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit diagnose --proof --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit proxy-disable --dry-run --fixture fixtures/dead_proxy_config/raw_signals.json
python -m windows_network_toolkit audit verify tests/fixtures/risk_analytics/audit_sample_chained/incidents.jsonl
python -m windows_network_toolkit governance-report --fixture fixtures/dead_proxy_config/raw_signals.json --format markdown
```

---

## Evidence and monitoring (read-only)

```powershell
python -m windows_network_toolkit proxy-watch --fixture tests/fixtures/enert/dead_proxy_59081.json --format json
python -m windows_network_toolkit proxy-health --fixture tests/fixtures/proxy_health_dead.json --json
python -m windows_network_toolkit tls-proof --url https://example.com --fixture tests/fixtures/enert/tls_cert_mismatch.json
python -m windows_network_toolkit website-risk --url https://example.com
python -m windows_network_toolkit evidence-report --fixture fixtures/dead_proxy_config/raw_signals.json --format markdown
python -m windows_network_toolkit proxy-timeline --audit
```

---

## LAN privacy and home/SOHO risk (read-only)

```powershell
python -m windows_network_toolkit lan-inventory --fixture examples/lan/executive_bundle.json
python -m windows_network_toolkit lan-risk-score --fixture examples/lan/executive_bundle.json
python -m windows_network_toolkit risk-executive-report --fixture examples/lan/executive_bundle.json --format both
python -m windows_network_toolkit router-import --type dns --input examples/router/dns_queries.csv --out .audit/router-dns.jsonl
```

Docs: [lan-privacy-monitor.md](lan-privacy-monitor.md) · [router-evidence-mode.md](router-evidence-mode.md)

---

## Risk and controls

```powershell
python -m windows_network_toolkit control-test --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
python -m windows_network_toolkit risk-assess --fixture tests/fixtures/case_studies/case_1_dead_wininet_proxy.json
```

---

## Replay and evaluation

```powershell
python -m windows_network_toolkit replay-demo --input tests/fixtures/proxy_transitions/proxy_enable_flapping_loop.jsonl
python -m windows_network_toolkit classifier-benchmark --cases examples/evaluation/classifier_benchmark_sample.json
pytest -q tests/evaluation/
```

---

## AI evals (fixture-only, no API keys)

```powershell
python -m windows_network_toolkit ai-eval --cases examples/ai_evals/support_bot_cases.json --format markdown
```

Doc: [ai-evals-feedback-loop.md](ai-evals-feedback-loop.md)

---

## API (optional, read-only demo)

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000
# GET /trisk/health  ·  GET /incidents  ·  GET /reports/executive
```

Full API reference: [cli_reference.md](cli_reference.md) · [api-trisk-examples.md](api-trisk-examples.md)

---

## Production-shaped Docker demo

```powershell
docker compose -f docker-compose.demo.yml up --build
python -m windows_network_toolkit reviewer-demo --mode mixed
```

Docs: [docker-production-shaped-demo.md](docker-production-shaped-demo.md) · [production-readiness-gap.md](production-readiness-gap.md)
