# Governance and Security — Power BI Layer

## Workspace assumptions

| Assumption | Portfolio default |
|------------|-------------------|
| Workspace type | Power BI Desktop `.pbix` locally (no published Service required) |
| License | Power BI Desktop (free) for portfolio demonstration |
| Gateway | Not required — CSV import mode |
| Premium capacity | Not assumed |

For enterprise deployment, map to a **Fabric / Premium** workspace with separate Dev/Test/Prod workspaces and deployment pipelines.

---

## Dataset refresh

| Mode | Portfolio | Production recommendation |
|------|-----------|---------------------------|
| Import | CSV from `analytics/powerbi/data` | Scheduled refresh from secure data lake |
| DirectQuery | Not used | Optional for live audit warehouse |
| Incremental refresh | N/A | Partition by `observed_at` month |

**Refresh cadence (design target):** Daily for executive dashboard; hourly for SOC-style operations (if audit stream available).

**Exporter integration:** Run `analytics-export-powerbi` in CI or orchestration **before** refresh — treat CSV as staging, not authoritative custody.

---

## Row-level security (RLS) design ideas

### By business unit (endpoint)

```text
[endpoint_id] starts with "EP-FIN" → Finance IT role
[endpoint_id] starts with "EP-SEC" → Cyber risk role only
```

### By classification sensitivity

| Role | Filter |
|------|--------|
| IT Support | All except POSSIBLE_MITM_RISK detail rows |
| Technology Risk | Full access |
| Audit (read-only) | All facts, no stakeholder PII |
| Executive | Aggregated — hide `endpoint_id` via aggregated table |

### Dynamic RLS pattern (DAX role filter example)

```dax
[endpoint_id] = USERPRINCIPALNAME ()
```

**Portfolio note:** Sample data uses synthetic `EP-*` identifiers — document mapping table in `dim_endpoint`.

---

## Sensitive endpoint identifiers

- Replace hostnames with `endpoint_id` tokens before export
- Do not import user display names or employee IDs into Power BI datasets
- `evidence_hash` is safe for integrity checks — not reversible to registry contents
- Avoid loading raw registry paths or proxy credentials into the semantic model

---

## Audit log immutability after CSV export

| Property | JSONL source | CSV export |
|----------|--------------|------------|
| Append-only | Yes (design intent) | No — snapshot overwrite |
| Hash chain | Verifiable | `hash_chain_valid` flag at export time only |
| Tamper detection | `audit verify` | Re-export required |

**Disclaimer for reports:** “CSV snapshot as of export timestamp; not a replacement for append-only audit custody.”

---

## AI-assisted explanation boundaries

| Allowed in Power BI narrative | Forbidden |
|------------------------------|-----------|
| Summarize incident counts | Imply AI authorized remediation |
| Explain proof-tier definitions | Malware or MITM confirmation rates |
| Link to human-review queue | Control effectiveness attestation |
| Show `ai_assisted_explanation` % | Autonomous action KPIs |

Filter visual subtitle: **“AI assists explanation only.”**

---

## No autonomous remediation

Measures like **Preview Only Rate** should be interpreted as **positive governance posture**, not failure to automate.

Do not create measures for:

- Unattended registry apply count
- Process kill success rate
- Firewall reset completion

These actions are blocked by platform policy contracts.

---

## No malware accusation

- `classification` labels are triage hypotheses
- `POSSIBLE_MITM_RISK` and `UNKNOWN_LOCAL_PROXY` must include limitation text on report pages
- Do not rename visuals to “Malware incidents” or “Compromise count”

---

## No regulatory sign-off

Dashboard footer (required on all pages):

> This report supports technology risk **triage and monitoring**. It does not constitute SOX ITGC attestation, regulatory compliance certification, or internal audit opinion.

---

## Related platform safety contracts

- `tests/test_policy_safety_contract.py`
- `tests/test_governance_safety_contracts.py`
- `analytics/powerbi/model/governance_and_security.md` (this document)
