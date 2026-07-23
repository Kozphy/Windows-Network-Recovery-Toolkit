package wnrt.remediation

# Default-deny policy for automated remediation.
default allow := false

default require_human_approval := true

read_only_actions := {
  "diagnose",
  "tls-proof",
  "website-risk",
  "evidence-report",
  "audit-verify",
  "replay"
}

high_impact_actions := {
  "proxy-disable",
  "registry-write",
  "firewall-change",
  "process-control",
  "credential-access"
}

allow if {
  input.action in read_only_actions
  input.scope.repository_path_valid == true
  input.evidence.complete == true
  input.policy_mode == "verify-only"
}

require_human_approval if {
  input.action in high_impact_actions
}

require_human_approval if {
  input.risk_score >= 60
}

require_human_approval if {
  input.ai_assisted == true
  input.action not in read_only_actions
}

deny_reason contains "unsupported action" if {
  not input.action in read_only_actions
  not input.action in high_impact_actions
}

deny_reason contains "incomplete evidence" if {
  input.evidence.complete != true
}

deny_reason contains "invalid execution scope" if {
  input.scope.repository_path_valid != true
}
