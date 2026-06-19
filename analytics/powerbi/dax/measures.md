# DAX Measures — Technology Risk Star Schema

**Model location:** Import `examples/powerbi/export/*.csv` into Power BI Desktop.

**Assumptions**

- Fact tables: `fact_incidents`, `fact_control_tests`, `fact_policy_decisions`
- Dimensions: `dim_date`, `dim_classification`, `dim_proof_tier`, `dim_stakeholder`
- `dim_date` marked as date table; single-direction relationships from dimensions to facts

---

## Executive KPIs

```dax
Total Incidents =
COUNTROWS ( fact_incidents )
```

```dax
High Risk Incidents =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[risk_level] IN { "HIGH", "CRITICAL" }
)
```

```dax
Unresolved Incidents =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[status] <> "RESOLVED"
)
```

```dax
Repeat Incident Rate =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_incidents ), fact_incidents[is_repeat] = TRUE () ),
    COUNTROWS ( fact_incidents ),
    0
)
```

---

## Control effectiveness

```dax
Control Tests Run =
COUNTROWS ( fact_control_tests )
```

```dax
Control Failure Rate =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_control_tests ),
        fact_control_tests[result] = "FAIL"
    ),
    COUNTROWS ( fact_control_tests ),
    0
)
```

```dax
Controls Not Tested =
CALCULATE (
    COUNTROWS ( fact_control_tests ),
    fact_control_tests[result] = "NOT_TESTED"
)
```

---

## Policy gate & human review

```dax
Remediation Previews =
CALCULATE (
    COUNTROWS ( fact_policy_decisions ),
    fact_policy_decisions[policy_action] = "PREVIEW"
)
```

```dax
Human Confirmation Required =
CALCULATE (
    COUNTROWS ( fact_policy_decisions ),
    fact_policy_decisions[human_confirmation_required] = TRUE ()
)
```

```dax
Blocked Actions =
CALCULATE (
    COUNTROWS ( fact_policy_decisions ),
    fact_policy_decisions[policy_action] = "BLOCK"
)
```

---

## Evidence quality

```dax
Incidents with Limitations =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    fact_incidents[has_limitations] = TRUE ()
)
```

```dax
Avg Confidence Score =
AVERAGE ( fact_incidents[confidence_score] )
```

```dax
Security Accusation Count =
CALCULATE (
    COUNTROWS ( fact_incidents ),
    RELATED ( dim_classification[is_security_accusation] ) = TRUE ()
)
```

> **Portfolio note:** This measure should normally return **zero**. Classification is not accusation.

---

## Time intelligence (Risk Trend page)

```dax
Incidents MTD =
TOTALMTD ( [Total Incidents], dim_date[date] )
```

```dax
Incidents Prior Month =
CALCULATE (
    [Total Incidents],
    DATEADD ( dim_date[date], -1, MONTH )
)
```

```dax
Incident Trend MoM % =
DIVIDE (
    [Incidents MTD] - [Incidents Prior Month],
    [Incidents Prior Month],
    BLANK ()
)
```

---

## Formatting recommendations

| Measure | Format |
|---------|--------|
| Control Failure Rate | Percentage, 1 decimal |
| Repeat Incident Rate | Percentage, 1 decimal |
| Mean time metrics | Decimal number + " min" suffix |
| Count measures | Whole number |
