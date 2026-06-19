"""Power BI star schema export — semantic model pack for PL-300 portfolio."""

from __future__ import annotations

import csv
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from src.platform_core.analytics.powerbi_export import (
    _control_test_rows,
    _date_key,
    _incident_rows_from_audit,
    _parse_ts,
    _risk_rating,
    portfolio_sample_tables,
)
from src.platform_core.analytics.summary import (
    _incident_key,
    _load_audit_records,
)
from src.platform_core.governance.chain_of_custody import verify_chain
from src.platform_core.governance.proof_tier import ProofTier
from src.platform_core.risk.business_impact_mapping import map_business_impact

SCHEMA_VERSION = "powerbi_star_export.v1"

SECRET_PATTERN = re.compile(
    r"(password|api[_-]?key|secret|credential|token|bearer\s)",
    re.IGNORECASE,
)

FACT_INCIDENTS_COLUMNS = [
    "incident_id",
    "audit_id",
    "date_key",
    "classification_key",
    "proof_tier_key",
    "stakeholder_key",
    "risk_level",
    "confidence_score",
    "execution_authority",
    "has_limitations",
    "created_at",
]

FACT_CONTROL_TESTS_COLUMNS = [
    "control_test_id",
    "incident_id",
    "date_key",
    "control_name",
    "control_domain",
    "result",
    "evidence_available",
    "limitation_count",
]

FACT_POLICY_DECISIONS_COLUMNS = [
    "decision_id",
    "incident_id",
    "date_key",
    "policy_action",
    "execution_authority",
    "human_confirmation_required",
    "confirmed",
    "blocked_reason",
]

DIM_CLASSIFICATION_COLUMNS = [
    "classification_key",
    "classification",
    "description",
    "is_security_accusation",
    "default_risk_level",
]

DIM_DATE_COLUMNS = [
    "date_key",
    "date",
    "year",
    "quarter",
    "month",
    "month_name",
    "week",
    "day",
]

DIM_STAKEHOLDER_COLUMNS = [
    "stakeholder_key",
    "stakeholder",
    "business_value",
]

DIM_PROOF_TIER_COLUMNS = [
    "proof_tier_key",
    "proof_tier",
    "description",
    "maturity_order",
]

STAR_CSV_FILES = [
    "fact_incidents.csv",
    "fact_control_tests.csv",
    "fact_policy_decisions.csv",
    "dim_classification.csv",
    "dim_date.csv",
    "dim_stakeholder.csv",
    "dim_proof_tier.csv",
    "README.md",
]

_CLASSIFICATION_CATALOG: list[tuple[int, str, str, str]] = [
    (1, "DEAD_PROXY_CONFIG", "WinINET points to localhost proxy without active listener", "MEDIUM"),
    (2, "WININET_WINHTTP_MISMATCH", "WinINET and WinHTTP proxy stacks diverge", "MEDIUM"),
    (3, "LOCAL_PROXY_ACTIVE", "Localhost proxy listener active", "LOW"),
    (4, "UNKNOWN_LOCAL_PROXY", "Unattributed localhost proxy — triage only", "HIGH"),
    (5, "PAC_CONFIGURED", "PAC URL configured for proxy routing", "MEDIUM"),
    (6, "POSSIBLE_MITM_RISK", "TLS path inconsistency — not confirmed MITM", "HIGH"),
    (7, "REVERTER_SUSPECTED", "Proxy settings reappear after remediation preview", "HIGH"),
    (8, "ERROR_INSUFFICIENT_DATA", "Insufficient evidence for classification", "LOW"),
    (9, "NO_PROXY", "No proxy misconfiguration in scope", "LOW"),
    (10, "UNCLASSIFIED", "Unclassified incident", "MEDIUM"),
]

_PROOF_TIER_CATALOG: list[tuple[int, str, str, int]] = [
    (0, ProofTier.T0_OBSERVATION_ONLY.value, "Observation only — not proof", 0),
    (1, ProofTier.T1_LOCAL_CONFIG_EVIDENCE.value, "Local configuration evidence", 1),
    (2, ProofTier.T2_RUNTIME_CORROBORATION.value, "Runtime path or listener corroboration", 2),
    (3, ProofTier.T3_BEHAVIORAL_REPRODUCTION.value, "Structured proof reproduction", 3),
    (4, ProofTier.T4_OPERATOR_CONFIRMED.value, "Operator-confirmed action in audit", 4),
]

_STAKEHOLDER_CATALOG: list[tuple[int, str, str]] = [
    (1, "IT Support", "Restore endpoint connectivity with evidence-backed remediation preview"),
    (2, "Technology Risk", "Governance decisions with proof tiers and limitations"),
    (3, "Cyber Risk Triage", "Review accusatory-adjacent labels without malware verdict"),
    (4, "Internal Audit", "Reconstruct decisions from audit trail and limitations"),
    (5, "Risk Committee", "Aggregated KPIs for steering and prioritization"),
    (6, "Platform Governance", "WinINET/WinHTTP stack alignment and change management"),
]

_STAKEHOLDER_FORUM_MAP = {
    "IT support": 1,
    "technology risk": 2,
    "cyber risk": 3,
    "audit": 4,
    "risk committee": 5,
    "platform governance": 6,
    "endpoint reliability": 6,
    "developer platform": 6,
    "security operations": 3,
    "change advisory": 6,
}


def _classification_key(name: str) -> int:
    upper = (name or "").upper()
    for cls_key, cls, _, _ in _CLASSIFICATION_CATALOG:
        if cls == upper:
            return cls_key
    return 10


def _proof_tier_key(tier: str) -> int:
    for tier_key, value, _, _ in _PROOF_TIER_CATALOG:
        if value == tier:
            return tier_key
    return 0


def _stakeholder_key(classification: str) -> int:
    forum = map_business_impact(classification).suggested_forum.lower()
    for fragment, key in _STAKEHOLDER_FORUM_MAP.items():
        if fragment in forum:
            return key
    return 2


def _confidence_score(flat: dict[str, Any]) -> float:
    ordinal = flat.get("confidence_ordinal")
    if ordinal is not None:
        return round(int(ordinal) / 5.0, 2)
    return 0.5


def build_dim_classification() -> list[dict[str, Any]]:
    return [
        {
            "classification_key": key,
            "classification": cls,
            "description": desc,
            "is_security_accusation": False,
            "default_risk_level": risk,
        }
        for key, cls, desc, risk in _CLASSIFICATION_CATALOG
    ]


def build_dim_proof_tier() -> list[dict[str, Any]]:
    return [
        {
            "proof_tier_key": key,
            "proof_tier": tier,
            "description": desc,
            "maturity_order": order,
        }
        for key, tier, desc, order in _PROOF_TIER_CATALOG
    ]


def build_dim_stakeholder() -> list[dict[str, Any]]:
    return [
        {"stakeholder_key": key, "stakeholder": name, "business_value": value}
        for key, name, value in _STAKEHOLDER_CATALOG
    ]


def build_dim_date_star(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build dim_date for star schema from fact date_key values."""
    keys = {int(r["date_key"]) for r in rows if r.get("date_key")}
    if not keys:
        keys = {20260601}
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    dim: list[dict[str, Any]] = []
    for key in sorted(keys):
        text = str(key)
        year = int(text[0:4])
        month = int(text[4:6])
        day = int(text[6:8])
        dt = date(year, month, day)
        dim.append(
            {
                "date_key": key,
                "date": dt.isoformat(),
                "year": year,
                "quarter": (month - 1) // 3 + 1,
                "month": month,
                "month_name": month_names[month - 1],
                "week": int(datetime(year, month, day, tzinfo=UTC).strftime("%V")),
                "day": day,
            }
        )
    return dim


def _flat_incidents_from_audit(
    audit_dir: Path,
    *,
    include_seed: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Return flat incident rows, raw audit records, and limitations."""
    records, _, limitations = _load_audit_records(audit_dir)
    chain_ok = True
    if records:
        chain_ok, _ = verify_chain(records)

    flats: list[dict[str, Any]] = []
    if include_seed or not records:
        flats.extend(portfolio_sample_tables()["incidents"])

    if records:
        inc, _, _, _ = _incident_rows_from_audit(records, hash_chain_valid=chain_ok)
        existing_ids = {r["incident_id"] for r in flats}
        for row in inc:
            if row["incident_id"] not in existing_ids:
                flats.append(row)

    flats.sort(key=lambda r: (r["incident_id"], r["observed_at"]))
    return flats, records, limitations


def _control_domain(control_name: str) -> str:
    if "proxy" in control_name.lower() or "wininet" in control_name.lower():
        return "Endpoint Reliability"
    if "PAC" in control_name:
        return "Platform Governance"
    return "Technology Risk Control"


def build_star_schema_tables(
    audit_dir: Path,
    *,
    include_seed: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Build star schema tables from audit directory and optional portfolio seed."""
    flats, records, _ = _flat_incidents_from_audit(audit_dir, include_seed=include_seed)
    control_flat = _control_test_rows(flats)

    fact_incidents: list[dict[str, Any]] = []
    fact_policy: list[dict[str, Any]] = []
    fact_controls: list[dict[str, Any]] = []

    for flat in flats:
        inc_id = flat["incident_id"]
        cls = flat["classification"]
        observed = _parse_ts(flat["observed_at"]) or datetime(2026, 6, 1, tzinfo=UTC)
        dk = _date_key(observed) or 20260601
        policy = flat.get("policy_decision") or "PREVIEW_ONLY"
        exec_auth = flat.get("execution_authority") or "preview_only"
        lim = int(flat.get("limitation_count") or 0)

        fact_incidents.append(
            {
                "incident_id": inc_id,
                "audit_id": flat.get("audit_id") or f"audit-{inc_id.lower()}",
                "date_key": dk,
                "classification_key": _classification_key(cls),
                "proof_tier_key": _proof_tier_key(flat.get("proof_tier", "")),
                "stakeholder_key": _stakeholder_key(cls),
                "risk_level": flat.get("risk_rating") or _risk_rating(cls),
                "confidence_score": _confidence_score(flat),
                "execution_authority": exec_auth,
                "has_limitations": lim > 0,
                "created_at": flat["observed_at"],
            }
        )

        human_conf = bool(flat.get("human_review_required")) or policy in (
            "HUMAN_REVIEW",
            "REQUIRE_TYPED_CONFIRMATION",
        )
        confirmed = exec_auth == "human_confirmed"
        blocked = policy == "BLOCK" or exec_auth == "blocked"
        fact_policy.append(
            {
                "decision_id": f"DEC-{inc_id}",
                "incident_id": inc_id,
                "date_key": dk,
                "policy_action": policy,
                "execution_authority": exec_auth,
                "human_confirmation_required": human_conf,
                "confirmed": confirmed,
                "blocked_reason": (
                    str(flat.get("blocked_action") or "Policy gate blocked destructive action")
                    if blocked
                    else ""
                ),
            }
        )

    for ct in control_flat:
        result = ct["control_test_result"]
        if result == "NOT_TESTED":
            mapped = "NOT_TESTED"
        elif result == "PARTIAL":
            mapped = "PARTIAL"
        elif result == "PASS":
            mapped = "PASS"
        else:
            mapped = "FAIL"
        observed = _parse_ts(ct["observed_at"])
        fact_controls.append(
            {
                "control_test_id": ct["control_test_id"],
                "incident_id": ct["incident_id"],
                "date_key": _date_key(observed) or 20260601,
                "control_name": ct["control_name"],
                "control_domain": _control_domain(ct["control_name"]),
                "result": mapped,
                "evidence_available": mapped != "NOT_TESTED",
                "limitation_count": 1 if mapped in ("PARTIAL", "FAIL") else 0,
            }
        )

    # Additional policy rows from raw audit blocked actions
    for row in records:
        inc_id = _incident_key(row)
        if str(row.get("decision", "")).lower() == "blocked":
            ts = _parse_ts(row.get("timestamp")) or datetime(2026, 6, 1, tzinfo=UTC)
            fact_policy.append(
                {
                    "decision_id": f"DEC-{inc_id}-BLK",
                    "incident_id": inc_id,
                    "date_key": _date_key(ts) or 20260601,
                    "policy_action": "BLOCK",
                    "execution_authority": "blocked",
                    "human_confirmation_required": True,
                    "confirmed": False,
                    "blocked_reason": str(row.get("blocked_action") or "Destructive action denied"),
                }
            )

    fact_policy.sort(key=lambda r: (r["decision_id"], r["incident_id"]))

    return {
        "fact_incidents": fact_incidents,
        "fact_control_tests": fact_controls,
        "fact_policy_decisions": fact_policy,
        "dim_classification": build_dim_classification(),
        "dim_date": build_dim_date_star(fact_incidents + fact_controls + fact_policy),
        "dim_stakeholder": build_dim_stakeholder(),
        "dim_proof_tier": build_dim_proof_tier(),
    }


def _export_readme() -> str:
    return """# Power BI Semantic Model Pack

Exported by `powerbi-export` from Technology Risk & Control Analytics Platform audit evidence.

## Tables

| File | Role |
|------|------|
| fact_incidents.csv | Incident grain — risk level, proof tier keys, execution authority |
| fact_control_tests.csv | Control test results per incident |
| fact_policy_decisions.csv | Policy gate outcomes — preview, block, human confirmation |
| dim_classification.csv | Triage labels — **is_security_accusation is always false** |
| dim_date.csv | Calendar dimension (mark as date table in Power BI) |
| dim_stakeholder.csv | Forum / audience for reporting |
| dim_proof_tier.csv | T0–T4 evidence maturity ordering |

## Relationships

- dim_date[date_key] → fact_*[date_key]
- dim_classification[classification_key] → fact_incidents[classification_key]
- dim_proof_tier[proof_tier_key] → fact_incidents[proof_tier_key]
- dim_stakeholder[stakeholder_key] → fact_incidents[stakeholder_key]
- fact_incidents[incident_id] → fact_control_tests[incident_id]
- fact_incidents[incident_id] → fact_policy_decisions[incident_id]

## Governance

- Classification is **not accusation** — not malware detection or EDR
- Remediation remains **preview-only** unless human_confirmed with audit evidence
- CSV snapshot — not append-only JSONL custody

See `examples/powerbi/report_blueprint.md` and `examples/powerbi/dax/measures.md`.
"""


def write_star_schema_csvs(tables: dict[str, list[dict[str, Any]]], out_dir: Path) -> None:
    """Write star schema CSV files and README to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "fact_incidents.csv": (FACT_INCIDENTS_COLUMNS, tables["fact_incidents"]),
        "fact_control_tests.csv": (FACT_CONTROL_TESTS_COLUMNS, tables["fact_control_tests"]),
        "fact_policy_decisions.csv": (FACT_POLICY_DECISIONS_COLUMNS, tables["fact_policy_decisions"]),
        "dim_classification.csv": (DIM_CLASSIFICATION_COLUMNS, tables["dim_classification"]),
        "dim_date.csv": (DIM_DATE_COLUMNS, tables["dim_date"]),
        "dim_stakeholder.csv": (DIM_STAKEHOLDER_COLUMNS, tables["dim_stakeholder"]),
        "dim_proof_tier.csv": (DIM_PROOF_TIER_COLUMNS, tables["dim_proof_tier"]),
    }
    for filename, (columns, rows) in mapping.items():
        path = out_dir / filename
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    (out_dir / "README.md").write_text(_export_readme(), encoding="utf-8")


def export_powerbi_star_schema(
    audit_dir: Path,
    out_dir: Path,
    *,
    include_seed: bool = True,
) -> dict[str, Any]:
    """Export Power BI star schema CSV pack from audit JSONL directory."""
    _, _, limitations = _load_audit_records(audit_dir)
    tables = build_star_schema_tables(audit_dir, include_seed=include_seed)
    write_star_schema_csvs(tables, out_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "powerbi-export",
        "feature": "Power BI Risk Analytics Export + Semantic Model Pack",
        "audit_dir": str(audit_dir.resolve()),
        "out_dir": str(out_dir.resolve()),
        "files_written": STAR_CSV_FILES,
        "record_counts": {k: len(v) for k, v in tables.items()},
        "limitations": limitations
        + [
            "Star schema export is a read-only analytics snapshot.",
            "Classification is not accusation; no autonomous remediation.",
        ],
    }


def scan_for_secrets(tables: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Return cell values matching secret-like patterns (for tests)."""
    hits: list[str] = []
    for rows in tables.values():
        for row in rows:
            for value in row.values():
                text = str(value)
                if SECRET_PATTERN.search(text):
                    hits.append(text)
    return hits
