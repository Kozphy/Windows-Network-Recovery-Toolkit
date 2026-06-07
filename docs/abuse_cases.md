# Abuse cases

Documented misuse scenarios and expected platform behavior.

## Malicious local process

**Scenario:** A process enables WinINET proxy and listens on localhost.

**Expected behavior:** Observations rank proxy drift; listener attribution is candidate evidence only. With Sysmon EID 13 fixtures, fusion may reach `REGISTRY_WRITER_OBSERVED` or `WRITER_AND_LISTENER_MATCH`. No automatic kill or registry revert.

## Compromised browser proxy settings

**Scenario:** Browser path fails while ICMP/TCP probes succeed.

**Expected behavior:** Layer classification surfaces L7/browser-path regression; incidents may open at medium severity when bypass contrast signals align. No silent repair.

## Malicious localhost listener

**Scenario:** Unknown process owns proxy port; registry writer telemetry missing.

**Expected behavior:** `LISTENER_OBSERVED` when listener supplied without writer telemetry. Limitations state listener ≠ writer proof.

## Abused API caller

**Scenario:** Client attempts `reset_firewall`, `process_kill`, or shell injection via action string.

**Expected behavior:** Policy BLOCK; tests reject injection patterns. Execute remains dry-run unless explicitly confirmed.

## Confused operator

**Scenario:** Operator assumes green ping means browser OK.

**Expected behavior:** Diagnosis separates layers; demo docs show bypass contrast. Preview-first workflow.

## Stale or misleading telemetry

**Scenario:** Imported Sysmon CSV from wrong time window.

**Expected behavior:** Fusion may return `NO_WRITER_EVIDENCE` or `INCONCLUSIVE`; limitations recommend widening window or re-export.

## False positive incident

**Scenario:** Benign dev proxy triggers incident rules.

**Expected behavior:** Operator transitions incident to `FALSE_POSITIVE`; metrics track `false_positive_rate`.
