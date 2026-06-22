"""Architecture module map for Technology Risk & Control Analytics Platform."""

from __future__ import annotations

MODULE_MAP = {
    "collectors": [
        "windows_network_toolkit/collectors/",
        "windows_network_toolkit/proxy_state.py",
        "windows_network_toolkit/proxy_owner.py",
        "windows_network_toolkit/collectors/playwright_collector.py",
    ],
    "classifiers": [
        "src/platform_core/classification/engine.py",
        "windows_network_toolkit/proxy_classification.py",
        "windows_network_toolkit/incident_classifier.py",
    ],
    "policy": [
        "src/platform_core/policy/engine.py",
        "src/platform_core/policy/outcome_normalizer.py",
        "config/policy/enterprise_default.yaml",
    ],
    "audit": [
        "src/platform_core/governance/chain_of_custody.py",
        "src/platform_core/audit/writer.py",
        "windows_network_toolkit/audit/",
    ],
    "reports": [
        "src/platform_core/evidence_report/generator.py",
        "src/platform_core/governance/audit_report.py",
        "windows_network_toolkit/analytics_pipeline.py",
    ],
    "cli": ["windows_network_toolkit/cli.py"],
}
