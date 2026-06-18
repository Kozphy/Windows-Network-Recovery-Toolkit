# DAX Measures — Technology Risk KPIs

**Table assumption:** Primary fact table is named `fact_incidents` in Power BI. Adjust table names if you rename on import.

**Boolean columns:** Imported as TRUE/FALSE text or Boolean — use `TRUE()` comparisons or normalize in Power Query.

---

## Incident volume

```dax
Total Incidents =
COUNTROWS ( fact_incidents )
```

```dax
High Risk Incidents =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[risk_rating] IN { "HIGH", "CRITICAL" }
)
```

```dax
High Risk Rate =
DIVIDE (
    [High Risk Incidents],
    [Total Incidents],
    0
)
```

```dax
Critical Incidents =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[risk_rating] = "CRITICAL"
)
```

```dax
Dead Proxy Incident Count =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[classification] = "DEAD_PROXY_CONFIG"
)
```

```dax
WinINET WinHTTP Mismatch Count =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[classification] = "WININET_WINHTTP_MISMATCH"
)
```

---

## Control testing

**Assumption:** `fact_control_tests` is a separate imported table.

```dax
Control Tests Passed =
CALCULATE (
    COUNTROWS ( fact_control_tests ),
    fact_control_tests[control_test_result] = "PASS"
)
```

```dax
Control Tests Failed =
CALCULATE (
    COUNTROWS ( fact_control_tests ),
    fact_control_tests[control_test_result] = "FAIL"
)
```

```dax
Control Pass Rate =
DIVIDE (
    [Control Tests Passed],
    COUNTROWS ( fact_control_tests ),
    0
)
```

---

## Remediation governance

```dax
Preview Only Actions =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[policy_decision] = "PREVIEW_ONLY"
)
```

```dax
Preview Only Rate =
DIVIDE (
    [Preview Only Actions],
    [Total Incidents],
    0
)
```

```dax
Policy Block Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_incidents ),
        fact_incidents[policy_decision] = "BLOCK"
    ),
    [Total Incidents],
    0
)
```

---

## Human review & audit

```dax
Human Review Pending =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[human_review_required] = TRUE ()
)
```

```dax
Audit Verification Pass Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_incidents ),
        fact_incidents[hash_chain_valid] = TRUE ()
    ),
    [Total Incidents],
    0
)
```

---

## Evidence quality

```dax
T3 Plus Evidence Coverage =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_incidents ),
        fact_incidents[proof_tier] IN {
            "T3_BEHAVIORAL_REPRODUCTION",
            "T4_OPERATOR_CONFIRMED"
        }
    ),
    [Total Incidents],
    0
)
```

```dax
Incidents with Limitations =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[limitation_count] > 0
)
```

```dax
AI Assisted Explanation Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_incidents ),
        fact_incidents[ai_assisted_explanation] = TRUE ()
    ),
    [Total Incidents],
    0
)
```

---

## Mean time to evidence

**Assumption:** `fact_audit_events` contains first `classification_observed` and earliest `observation` per incident. Create a calculated column or staging table in Power Query:

```dax
Mean Time to Evidence (Minutes) =
VAR IncidentTable =
    ADDCOLUMNS (
        VALUES ( fact_incidents[incident_id] ),
        "@Minutes",
            VAR FirstEvent =
                MINX (
                    FILTER (
                        fact_audit_events,
                        fact_audit_events[incident_id] = EARLIER ( fact_incidents[incident_id] )
                    ),
                    fact_audit_events[observed_at]
                )
            VAR ClassifiedEvent =
                MINX (
                    FILTER (
                        fact_audit_events,
                        fact_audit_events[incident_id] = EARLIER ( fact_incidents[incident_id] )
                            && fact_audit_events[event_type] = "classification_observed"
                    ),
                    fact_audit_events[observed_at]
                )
            RETURN
                DATEDIFF ( FirstEvent, ClassifiedEvent, MINUTE )
    )
RETURN
    AVERAGEX ( IncidentTable, [@Minutes] )
```

**Portfolio note:** With sparse audit samples, this measure may return BLANK — document as a modeling exercise, not production SLA.

---

## Formatting recommendations

| Measure | Format |
|---------|--------|
| High Risk Rate, Control Pass Rate, Preview Only Rate | Percentage, 1 decimal |
| Mean Time to Evidence | Whole number minutes |
| Count measures | Whole number |

---

## Limitations (display on report)

Add a card visual with static text:

> Measures reflect triage and control design effectiveness. They do not attest regulatory compliance, malware absence, or autonomous remediation safety.
