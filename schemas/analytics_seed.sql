-- Sample seed for portfolio SQL demos (see docs/analytics_data_model.md)

INSERT INTO incidents (incident_id, created_at, classification, confidence_score, evidence_tier, policy_decision, remediation_status) VALUES
('CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:25:00Z', 'DEAD_PROXY_CONFIG', 0.92, 'proof', 'PREVIEW_ONLY', 'preview_only'),
('INC-UNKNOWN-PROXY-017', '2026-06-10T17:00:00Z', 'UNKNOWN_LOCAL_PROXY', 0.35, 'observation', 'REQUIRE_TYPED_CONFIRMATION', 'open');

INSERT INTO evidence_events (event_id, incident_id, event_time, source, signal_type, observed_value, claim_strength) VALUES
('ev-001', 'CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:25:10Z', 'wininet_registry', 'proxy_server', '127.0.0.1:59081', 'observation'),
('ev-002', 'CASE_1_DEAD_WININET_PROXY', '2026-06-11T04:28:00Z', 'proof_engine', 'wininet_winhttp_comparison', 'supported', 'proof');

INSERT INTO proof_results (proof_id, incident_id, hypothesis, conclusion_status, confidence_score, tested_at) VALUES
('pr-001', 'CASE_1_DEAD_WININET_PROXY', 'Dead WinINET localhost proxy', 'supported', 0.92, '2026-06-11T04:28:30Z');

INSERT INTO policy_decisions (policy_decision_id, incident_id, decision, blocked_action, decided_at) VALUES
('pd-001', 'CASE_1_DEAD_WININET_PROXY', 'PREVIEW_ONLY', NULL, '2026-06-11T04:30:00Z'),
('pd-002', 'INC-UNKNOWN-PROXY-017', 'BLOCKED', 'KILL_PROXY_PROCESS', '2026-06-10T17:15:00Z');

INSERT INTO remediation_previews (preview_id, incident_id, proposed_action, dry_run, executed, previewed_at) VALUES
('rp-001', 'CASE_1_DEAD_WININET_PROXY', 'DISABLE_WININET_PROXY', TRUE, FALSE, '2026-06-11T04:31:00Z');

INSERT INTO audit_events (audit_event_id, incident_id, audit_file, action, decision, event_time, hash_chain_valid) VALUES
('ae-001', 'CASE_1_DEAD_WININET_PROXY', 'incidents.jsonl', 'remediation_preview', 'allowed', '2026-06-11T04:30:00Z', NULL),
('ae-002', 'INC-UNKNOWN-PROXY-017', 'incidents.jsonl', 'remediation_execute', 'blocked', '2026-06-10T17:16:00Z', NULL);
