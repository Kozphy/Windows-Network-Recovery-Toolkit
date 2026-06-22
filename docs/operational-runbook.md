# Operational Runbook

Portfolio-scope procedures for the production-shaped demo stack.

## Health checks

```powershell
curl -s http://127.0.0.1:8000/trisk/health
curl -s http://127.0.0.1:8000/metrics | head
make prod-demo-health
```

## API up, worker not processing

1. Check Redis: `docker compose exec redis redis-cli ping`
2. Check worker logs: `docker compose logs worker`
3. Verify `REDIS_URL` matches compose network
4. Requeue stuck jobs: restart worker container (idempotent jobs safe)

## Postgres full or unreachable

1. Check `docker compose ps postgres`
2. Inspect disk: `docker system df`
3. Demo recovery: `docker compose down -v` (destroys demo data — acceptable for portfolio)

## Audit verify failure

```powershell
python -m windows_network_toolkit audit verify <path-to.jsonl>
```

- **Chain break:** investigate tamper or partial write; restore from backup JSONL
- **Missing genesis:** re-export from Postgres if dual-write intact

## Quarantine queue (malformed evidence)

- Evidence with `classification_status=quarantined` in Postgres
- Review `limitations` and validation errors in API response
- Do not retry without fixing payload — not a malware quarantine

## Safe remediation reminder

This runbook does **not** authorize registry mutation. Remediation remains CLI preview + typed confirmation only.

## Escalation (portfolio)

No on-call. For demo failures: restart compose stack, run `pytest -q`, check CI logs.
