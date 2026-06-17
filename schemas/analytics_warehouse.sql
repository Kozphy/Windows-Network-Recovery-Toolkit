-- Technology Risk & Control Analytics — warehouse DDL
-- Portable ANSI SQL (PostgreSQL / SQLite / BigQuery compatible with minor type tweaks)
-- See docs/analytics_data_model.md for field definitions and ETL mapping.

CREATE TABLE IF NOT EXISTS endpoints (
    endpoint_id     TEXT PRIMARY KEY,
    hostname        TEXT NOT NULL,
    environment     TEXT NOT NULL DEFAULT 'production',
    owner_team      TEXT,
    criticality     TEXT NOT NULL DEFAULT 'medium'
        CHECK (criticality IN ('low', 'medium', 'high', 'critical')),
    last_seen       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id         TEXT PRIMARY KEY,
    endpoint_id         TEXT NOT NULL REFERENCES endpoints(endpoint_id),
    created_at          TIMESTAMPTZ NOT NULL,
    closed_at           TIMESTAMPTZ,
    classification      TEXT NOT NULL,
    secondary_signals   TEXT,  -- JSON array serialized
    confidence_score    REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    evidence_tier       TEXT NOT NULL
        CHECK (evidence_tier IN ('observation', 'correlation', 'proof', 'attribution', 'final_causation')),
    business_impact     TEXT NOT NULL DEFAULT 'medium'
        CHECK (business_impact IN ('low', 'medium', 'high', 'critical')),
    policy_decision     TEXT,
    remediation_status  TEXT NOT NULL DEFAULT 'open'
        CHECK (remediation_status IN ('open', 'preview_only', 'pending_approval', 'applied', 'closed', 'escalated')),
    audit_chain_valid   BOOLEAN,
    diagnosis_started_at TIMESTAMPTZ,
    diagnosis_completed_at TIMESTAMPTZ,
    source_case_id      TEXT,
    limitations         TEXT  -- JSON array serialized
);

CREATE INDEX IF NOT EXISTS idx_incidents_classification ON incidents(classification);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_endpoint ON incidents(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_incidents_evidence_tier ON incidents(evidence_tier);

CREATE TABLE IF NOT EXISTS evidence_events (
    event_id        TEXT PRIMARY KEY,
    incident_id     TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    event_time      TIMESTAMPTZ NOT NULL,
    source          TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    observed_value  TEXT,
    claim_strength  TEXT NOT NULL DEFAULT 'observation'
        CHECK (claim_strength IN ('observation', 'correlation', 'proof', 'attribution', 'final_causation')),
    limitation      TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_incident ON evidence_events(incident_id);
CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence_events(claim_strength);

CREATE TABLE IF NOT EXISTS control_tests (
    test_id             TEXT PRIMARY KEY,
    incident_id         TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    control_name        TEXT NOT NULL,
    control_objective   TEXT,
    pass_fail           TEXT NOT NULL
        CHECK (pass_fail IN ('PASS', 'FAIL', 'WARNING', 'NOT_TESTED')),
    evidence_required   BOOLEAN NOT NULL DEFAULT TRUE,
    evidence_available  BOOLEAN NOT NULL DEFAULT FALSE,
    tested_at           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_tests_incident ON control_tests(incident_id);

CREATE TABLE IF NOT EXISTS policy_decisions (
    policy_decision_id  TEXT PRIMARY KEY,
    incident_id         TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    decision            TEXT NOT NULL,
    reason              TEXT,
    blocked_action      TEXT,
    approval_required   BOOLEAN NOT NULL DEFAULT TRUE,
    rollback_required   BOOLEAN NOT NULL DEFAULT TRUE,
    decided_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remediation_previews (
    preview_id                  TEXT PRIMARY KEY,
    incident_id                 TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    proposed_action             TEXT NOT NULL,
    dry_run                     BOOLEAN NOT NULL DEFAULT TRUE,
    typed_confirmation_required BOOLEAN NOT NULL DEFAULT TRUE,
    rollback_plan_available     BOOLEAN NOT NULL DEFAULT TRUE,
    executed                    BOOLEAN NOT NULL DEFAULT FALSE,
    previewed_at                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at                 TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_chain_checks (
    check_id            TEXT PRIMARY KEY,
    incident_id         TEXT NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    audit_file          TEXT NOT NULL,
    hash_chain_valid    BOOLEAN NOT NULL,
    checked_at          TIMESTAMPTZ NOT NULL
);
