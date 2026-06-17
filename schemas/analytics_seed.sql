-- Sample seed data for analytics warehouse demos (SQLite / PostgreSQL)
-- Load after schemas/analytics_warehouse.sql
-- See docs/analytics_data_model.md and docs/sql_analytics_queries.md

INSERT INTO endpoints (endpoint_id, hostname, environment, owner_team, criticality, last_seen) VALUES
('ep-59081-001', 'LAPTOP-FIN-042', 'production', 'Endpoint Engineering', 'high', '2026-06-11T04:31:31Z'),
('ep-fleet-017', 'WS-TRADING-017', 'production', 'Trading Technology', 'critical', '2026-06-10T18:00:00Z'),
('ep-corp-088', 'LAPTOP-CORP-088', 'corp', 'IT Operations', 'medium', '2026-06-09T12:00:00Z');

INSERT INTO incidents (
    incident_id, endpoint_id, created_at, closed_at, classification, secondary_signals,
    confidence_score, evidence_tier, business_impact, policy_decision, remediation_status,
    audit_chain_valid, diagnosis_started_at, diagnosis_completed_at, source_case_id
) VALUES
('CASE_1_DEAD_WININET_PROXY', 'ep-59081-001', '2026-06-11T04:25:00Z', NULL,
 'DEAD_PROXY_CONFIG', '["WININET_WINHTTP_MISMATCH","LOCALHOST_PROXY"]',
 0.92, 'proof', 'medium', 'PREVIEW_ONLY', 'preview_only', TRUE,
 '2026-06-11T04:26:00Z', '2026-06-11T04:28:30Z', 'case_1_dead_wininet_proxy.json'),
('INC-UNKNOWN-PROXY-017', 'ep-fleet-017', '2026-06-10T17:00:00Z', NULL,
 'UNKNOWN_LOCAL_PROXY', '["LOCALHOST_PROXY"]',
 0.35, 'observation', 'high', 'REQUIRE_TYPED_CONFIRMATION', 'open', NULL,
 '2026-06-10T17:05:00Z', '2026-06-10T17:12:00Z', 'unknown_localhost_proxy.json'),
('INC-DRIFT-088', 'ep-corp-088', '2026-06-01T09:00:00Z', '2026-06-01T11:00:00Z',
 'DEAD_PROXY_CONFIG', '["WININET_WINHTTP_MISMATCH"]',
 0.88, 'proof', 'low', 'PREVIEW_ONLY', 'closed', TRUE,
 '2026-06-01T09:10:00Z', '2026-06-01T09:20:00Z', 'dead_proxy_59081.json');

INSERT INTO evidence_events (event_id, incident_id, event_time, source, signal_type, observed_value, claim_strength, limitation) VALUES
('ev-001', 'CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:25:10Z', 'wininet_registry', 'proxy_server', '127.0.0.1:59081', 'observation', NULL),
('ev-002', 'CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:25:15Z', 'netstat', 'listener_found', 'false', 'observation', 'Listener absence does not prove malware'),
('ev-003', 'CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:28:00Z', 'proof_engine', 'wininet_winhttp_comparison', 'supported', 'proof', 'Does not prove MITM');

INSERT INTO control_tests (test_id, incident_id, control_name, control_objective, pass_fail, evidence_required, evidence_available, tested_at) VALUES
('CT_PROXY_DRIFT', 'CASE_1_DEAD_WININET_PROXY', 'Proxy drift detection', 'Configuration monitoring', 'FAIL', TRUE, TRUE, '2026-06-11T04:29:00Z'),
('CT_REMEDIATION_SAFETY', 'CASE_1_DEAD_WININET_PROXY', 'Policy-gated remediation', 'Change management', 'PASS', TRUE, TRUE, '2026-06-11T04:29:05Z');

INSERT INTO policy_decisions (policy_decision_id, incident_id, decision, reason, blocked_action, approval_required, rollback_required, decided_at) VALUES
('pd-001', 'CASE_1_DEAD_WININET_PROXY', 'PREVIEW_ONLY', 'Dry-run default; typed confirmation required', NULL, TRUE, TRUE, '2026-06-11T04:30:00Z'),
('pd-002', 'INC-UNKNOWN-PROXY-017', 'REQUIRE_TYPED_CONFIRMATION', 'Low confidence; security review advised', 'process_kill', TRUE, TRUE, '2026-06-10T17:15:00Z');

INSERT INTO remediation_previews (preview_id, incident_id, proposed_action, dry_run, typed_confirmation_required, rollback_plan_available, executed, previewed_at) VALUES
('rp-001', 'CASE_1_DEAD_WININET_PROXY', 'DISABLE_WININET_PROXY', TRUE, TRUE, TRUE, FALSE, '2026-06-11T04:31:00Z');

INSERT INTO audit_chain_checks (check_id, incident_id, audit_file, hash_chain_valid, checked_at) VALUES
('ac-001', 'CASE_1_DEAD_WININET_PROXY', '.audit/incident_CASE_1.jsonl', TRUE, '2026-06-11T04:32:00Z'),
('ac-002', 'INC-DRIFT-088', '.audit/incident_INC-DRIFT-088.jsonl', TRUE, '2026-06-01T11:30:00Z');
