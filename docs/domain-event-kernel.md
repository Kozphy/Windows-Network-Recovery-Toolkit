# Domain event kernel (Level 1)

One **versioned envelope**, one **append path**, one **verify path** for audit / decision / guardian custody.

This is a **local hash-chained JSONL** kernel — not WORM, SIEM, Kafka, or multi-tenant SaaS.

## Envelope (`wnrt.domain_event.v1`)

| Field | Role |
|-------|------|
| `schema_version` | `wnrt.domain_event.v1` |
| `event_id` / `audit_id` | Stable ID (UUID) |
| `event_type` | e.g. `guardian.check`, `decision.diagnosis` |
| `timestamp_utc` | Event time (UTC Z) |
| `source` | Component (`proxy_guardian`, `src.cli.diagnose`, …) |
| `tenant_id` | Deployment scope (`WNT_TENANT_ID` or `local`) |
| `correlation_id` / `trace_id` | Run / diagnosis correlation |
| `actor` | Writer attribution when known |
| `payload` | Domain-specific object |
| `custody` | Model metadata + limitations (not hash duplicates) |
| `previous_hash` / `current_hash` / `signature_status` | Chain integrity |

Legacy rows (`erp.audit.v1`) remain readable and chain-verifiable.

## API

| Function | Module |
|----------|--------|
| `append_domain_event(...)` | `src.platform_core.domain_events.writer` |
| `verify_domain_stream(path)` | `src.platform_core.domain_events.verify` |
| `append_audit(...)` | wraps domain writer; returns `AuditRecord` |
| `append_custody_event(...)` | guardian/proxy-fix → domain writer |

## Verification command (single path)

```powershell
$env:PYTHONPATH = (Get-Location).Path

# Chain + envelope (tip ignored for exit code unless flags set)
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl

# Chain + tip
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --check-tip

# Fail if tip missing
python -m windows_network_toolkit audit verify .audit/canonical_custody.jsonl --require-tip
```

## README demo

### 1. Generate representative events

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:WNT_AUDIT_DIR = ".audit_demo"
python -c @"
from pathlib import Path
from src.platform_core.domain_events.writer import append_domain_event, reset_domain_chain_for_tests
reset_domain_chain_for_tests()
p = Path('.audit_demo/canonical_custody.jsonl')
append_domain_event('guardian.check', source='proxy_guardian', payload={'classification': 'NO_PROXY'}, path=p)
append_domain_event('decision.diagnosis', source='src.cli.diagnose', action_type='decision_created', payload={'diagnosis_id': 'demo-1'}, path=p)
print('wrote', p)
"@
```

### 2. Inspect the unified stream

```powershell
python -c @"
from pathlib import Path
from src.platform_core.domain_events.verify import inspect_stream
import json
print(json.dumps(inspect_stream(Path('.audit_demo/canonical_custody.jsonl')), indent=2))
"@
```

### 3. Verify successfully

```powershell
python -m windows_network_toolkit audit verify .audit_demo/canonical_custody.jsonl --check-tip
```

Expect `"verified": true`.

### 4. Detect deliberate tampering

```powershell
python -c @"
from pathlib import Path
import json
p = Path('.audit_demo/canonical_custody.jsonl')
lines = p.read_text(encoding='utf-8').splitlines()
row = json.loads(lines[0])
row['payload']['tampered'] = True
lines[0] = json.dumps(row)
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('tampered first event payload')
"@
python -m windows_network_toolkit audit verify .audit_demo/canonical_custody.jsonl --check-tip
```

Expect `"verified": false` and `"chain_verified": false`.

Golden fixture: `tests/fixtures/domain_events/valid_stream.jsonl`.

## Limitations (honest)

- Observation ≠ proof; chain verify ≠ payload truth  
- Same-host tip ≠ WORM  
- Not all repo JSONL files are on this kernel yet (see [domain-event-inventory.md](domain-event-inventory.md))  
- Confirmation token strings are never stored in custody payloads  

## Related

- [domain-event-inventory.md](domain-event-inventory.md)  
- [audit-custody.md](audit-custody.md)  
- [production-readiness-gap.md](production-readiness-gap.md)  
