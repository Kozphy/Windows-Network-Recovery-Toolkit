-- Technology Risk & Control Analytics — portfolio warehouse DDL
-- See docs/analytics_data_model.md

CREATE TABLE IF NOT EXISTS incidents (
    incident_id         TEXT PRIMARY KEY,
    endpoint_id         TEXT,
    created_at          TIMESTAMPTZ NOT NULL,
    closed_at           TIMESTAMPTZ,
    classification      TEXT NOT NULL,
    secondary_signals   TEXT,
    confidence_score    REAL,
    evidence_tier       TEXT,
    business_impact     TEXT DEFAULT 'medium',
    policy_decision     TEXT,
    remediation_status  TEXT DEFAULT 'open',
    audit_chain_valid   BOOLEAN,
    diagnosis_started_at TIMESTAMPTZ,
    diagnosis_completed_at TIMESTAMPTZ,
    limitations         TEXT
);

CREATE TABLE IF NOT EXISTS evidence_events (
    event_id        TEXT PRIMARY KEY,
    incident_id     TEXT NOT NULL REFERENCES incidents(incident_id),
    event_time      TIMESTAMPTZ NOT NULL,
    source          TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    observed_value  TEXT,
    claim_strength  TEXT DEFAULT 'observation',
    limitation      TEXT
);

CREATE TABLE IF NOT EXISTS proof_results (
    proof_id        TEXT PRIMARY KEY,
    incident_id     TEXT NOT NULL REFERENCES incidents(incident_id),
    hypothesis      TEXT,
    conclusion_status TEXT,
    confidence_score REAL,
    proof_attempts  TEXT,
    tested_at       TIMESTAMPTZ NOT NULL,
    limitations     TEXT
);

CREATE TABLE IF NOT EXISTS policy_decisions (
    policy_decision_id  TEXT PRIMARY KEY,
    incident_id         TEXT NOT NULL REFERENCES incidents(incident_id),
    decision            TEXT NOT NULL,
    reason              TEXT,
    blocked_action      TEXT,
    approval_required   BOOLEAN DEFAULT TRUE,
    rollback_required   BOOLEAN DEFAULT TRUE,
    decided_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remediation_previews (
    preview_id                  TEXT PRIMARY KEY,
    incident_id                 TEXT NOT NULL REFERENCES incidents(incident_id),
    proposed_action             TEXT NOT NULL,
    dry_run                     BOOLEAN NOT NULL DEFAULT TRUE,
    typed_confirmation_required BOOLEAN NOT NULL DEFAULT TRUE,
    rollback_plan_available     BOOLEAN NOT NULL DEFAULT TRUE,
    executed                    BOOLEAN NOT NULL DEFAULT FALSE,
    previewed_at                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at                 TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id  TEXT PRIMARY KEY,
    incident_id     TEXT,
    audit_file      TEXT,
    action          TEXT,
    decision        TEXT,
    actor           TEXT,
    event_time      TIMESTAMPTZ NOT NULL,
    hash_chain_valid BOOLEAN,
    payload         TEXT
);

CREATE INDEX IF NOT EXISTS idx_incidents_classification ON incidents(classification);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_incident ON evidence_events(incident_id);
CREATE INDEX IF NOT EXISTS idx_proof_incident ON proof_results(incident_id);
CREATE INDEX IF NOT EXISTS idx_policy_incident ON policy_decisions(incident_id);
CREATE INDEX IF NOT EXISTS idx_remediation_incident ON remediation_previews(incident_id);
CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_events(incident_id);
