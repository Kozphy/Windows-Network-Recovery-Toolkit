"""Classification, policy, timeline, and evidence tree tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.classification.models import ProcessClassificationInput
from src.classification.process_classifier import classify_process
from src.policy.models import ProxyPolicyUserConfig
from src.policy.proxy_policy_engine import evaluate_proxy_policy
from src.proxy_guard.audit import emit_proxy_change_detected_audit
from src.proxy_guard.incident_pipeline import analyze_incident_from_row, build_incident_timeline
from src.proxy_guard.proxy_allowlist import ProxyAllowlist
from src.replay.proxy_timeline import build_proxy_timeline, render_timeline_json
from src.reports.evidence_tree import build_evidence_tree, render_evidence_tree_markdown
from src.telemetry.sysmon_reader import parse_sysmon_xml_batch

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sysmon"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _sysmon_bundle() -> list:
    return parse_sysmon_xml_batch(
        [
            _load("eid13_proxyserver_node.xml"),
            _load("eid13_proxyenable_dword1.xml"),
            _load("eid1_node_from_powershell.xml"),
            _load("eid1_powershell_parent.xml"),
            _load("eid3_listener_64394.xml"),
        ]
    )


def _transition_row(**overrides) -> dict:
    base = {
        "timestamp": "2026-06-08T05:00:55Z",
        "event": "proxy_change_detected",
        "diff": {
            "changed": True,
            "risk_level": "high",
            "changed_fields": ["ProxyServer", "ProxyEnable"],
            "before": {"proxy_server": None, "proxy_enable": 0},
            "after": {"proxy_server": "127.0.0.1:64394", "proxy_enable": 1},
        },
        "attribution": {
            "confidence": 0.7,
            "primary_suspect": {"name": "node.exe", "pid": 12345, "parent_name": "powershell.exe"},
        },
        "decision": {"action": "alert", "reason": "high_risk"},
    }
    base.update(overrides)
    return base


def test_cursor_node_proxy_allowed_or_observe() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        command_line="node.exe extension-host",
        parent_image_path=r"C:\Users\me\AppData\Local\Programs\cursor\Cursor.exe",
        parent_command_line="Cursor.exe",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:64394",
        localhost_port=64394,
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    al = ProxyAllowlist(
        trusted_processes=frozenset({"cursor.exe", "node.exe"}),
        trusted_paths=frozenset({r"c:\users\me\appdata\local\programs\cursor"}),
        trusted_commandline_keywords=frozenset(),
    )
    cls = classify_process(inp, allowlist=al)
    assert cls.classification.value == "KNOWN_CURSOR_PROXY"
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "127.0.0.1:64394", "proxy_enable": 1},
        config=ProxyPolicyUserConfig(allow_known_cursor=True, cursor_action="OBSERVE"),
    )
    assert pol.decision.value in ("OBSERVE", "ALLOW")


def test_vscode_extension_observed() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        command_line="node.exe --max-old-space-size=8192",
        parent_image_path=r"C:\Program Files\Microsoft VS Code\Code.exe",
        parent_command_line="Code.exe --extensionDevelopmentPath=...",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:8080",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    al = ProxyAllowlist(
        trusted_processes=frozenset({"code.exe", "node.exe"}),
        trusted_paths=frozenset({r"c:\program files\microsoft vs code"}),
        trusted_commandline_keywords=frozenset({"extension"}),
    )
    cls = classify_process(inp, allowlist=al)
    assert cls.classification.value == "KNOWN_VSCODE_EXTENSION"
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "127.0.0.1:8080"},
        config=ProxyPolicyUserConfig(vscode_action="OBSERVE"),
    )
    assert pol.decision.value == "OBSERVE"


def test_unknown_node_powershell_alert() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        parent_image_path=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:64394",
        registry_target=r"HKU\S-1-5-21\...\ProxyServer",
        registry_value_name="proxyserver",
    )
    cls = classify_process(inp)
    assert cls.classification.value in ("REGISTRY_WRITER_CONFIRMED", "UNKNOWN_LOCAL_PROXY")
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "127.0.0.1:64394"},
    )
    assert pol.decision.value == "ALERT"


def test_obfuscated_powershell_suspicious() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Users\me\AppData\Local\Temp\node.exe",
        parent_image_path=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        parent_command_line="powershell.exe -enc SGVsbG8gV29ybGQ=",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:9999",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    cls = classify_process(inp)
    assert cls.classification.value == "SUSPICIOUS_PROXY"
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "127.0.0.1:9999"},
    )
    assert pol.decision.value == "BLOCK_RECOMMENDED"
    assert pol.requires_confirmation


def test_external_proxy_alert() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\evil\proxy.exe",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="203.0.113.50:8080",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
        registry_details="203.0.113.50:8080",
    )
    cls = classify_process(inp)
    assert cls.classification.value == "POSSIBLE_MITM_RISK"
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "203.0.113.50:8080"},
        risk_level="high",
    )
    assert pol.decision.value in ("ALERT", "BLOCK_RECOMMENDED", "ESCALATE_REVIEW")


def test_autoconfigurl_changed_alert() -> None:
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification="KNOWN_DEV_PROXY",
        current_proxy_state={"auto_config_url": "http://evil/pac.js"},
        changed_fields=["AutoConfigURL"],
    )
    assert pol.decision.value == "ALERT"


def test_registry_writer_no_listener(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    row = _transition_row(attribution={"confidence": 0.0, "primary_suspect": None})
    monkeypatch.setattr("src.correlation.proxy_causation.query_sysmon_events", lambda *a, **k: _sysmon_bundle())
    bundle = analyze_incident_from_row(row, repo_root=tmp_path)
    assert bundle["causation"]["causation_level"] == "FINAL_CAUSATION"
    assert (row.get("attribution") or {}).get("primary_suspect") is None
    assert bundle["classification"]["label"] in ("REGISTRY_WRITER_CONFIRMED", "UNKNOWN_LOCAL_PROXY")


def test_listener_no_registry_correlation_alert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    row = _transition_row()
    events = []

    def no_sysmon(*a, **k):
        return events

    monkeypatch.setattr("src.correlation.proxy_causation.query_sysmon_events", no_sysmon)
    bundle = analyze_incident_from_row(row, repo_root=tmp_path)
    assert bundle["causation"]["causation_level"] == "CORRELATION_ONLY"
    assert bundle["policy"]["decision"] == "CORRELATION_ONLY_ALERT"


def test_python_false_attribution_low_confidence() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Python311\python.exe",
        command_line="python -m nvidia_smi_helper",
        causation_level="CORRELATION_ONLY",
        has_listener_only=True,
        proxy_server_after="127.0.0.1:64394",
        localhost_port=64394,
    )
    cls = classify_process(inp)
    assert cls.classification.value in ("CORRELATION_ONLY", "UNKNOWN")
    assert cls.confidence <= 0.45


def test_timeline_preserves_event_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.correlation.proxy_causation.query_sysmon_events", lambda *a, **k: _sysmon_bundle())
    emit_proxy_change_detected_audit(
        tmp_path,
        diff=_transition_row()["diff"],
        attribution=_transition_row()["attribution"],
        decision=_transition_row()["decision"],
    )
    events = build_incident_timeline(tmp_path, since_minutes=120, run=None)
    kinds = [e.event_type.value for e in events]
    assert "PROXY_STATE_CHANGED" in kinds
    if "PROCESS_CREATED" in kinds and "PROXY_STATE_CHANGED" in kinds:
        assert kinds.index("PROCESS_CREATED") < kinds.index("PROXY_STATE_CHANGED")
    if "PROXY_STATE_CHANGED" in kinds and "POLICY_DECISION_CREATED" in kinds:
        assert kinds.index("PROXY_STATE_CHANGED") < kinds.index("POLICY_DECISION_CREATED")
    payload = json.loads(render_timeline_json(events))
    timestamps = [e["timestamp_utc"] for e in payload["events"] if e["timestamp_utc"]]
    assert timestamps == sorted(timestamps)


def test_evidence_tree_structure() -> None:
    row = _transition_row()
    causation = {
        "causation_level": "FINAL_CAUSATION",
        "confidence": 0.95,
        "writer_process": "node.exe",
        "parent_process": "powershell.exe",
        "matched_registry_target": "ProxyServer",
        "matched_registry_details": "127.0.0.1:64394",
        "process_tree": [],
        "network_events": [],
        "explanation": "proof",
    }
    cls = {"label": "UNKNOWN_LOCAL_PROXY", "confidence": 0.5, "explanation": "unknown"}
    pol = {"action": "ALERT", "confidence": 0.8, "explanation": "alert", "requires_human_review": True}
    tree = build_evidence_tree(transition_row=row, causation=causation, classification=cls, policy=pol)
    md = render_evidence_tree_markdown(tree)
    assert "Observation" in md
    assert "Registry Writer Proof" in md
    assert "Recommended Action" in md


def test_known_dev_proxy_observe() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        command_line="npm run dev -- --port 3000",
        causation_level="FINAL_CAUSATION",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:3000",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    cls = classify_process(inp)
    assert cls.classification.value == "KNOWN_DEV_PROXY"
    pol = evaluate_proxy_policy(
        causation_level="FINAL_CAUSATION",
        classification=cls,
        current_proxy_state={"proxy_server": "127.0.0.1:3000"},
        config=ProxyPolicyUserConfig(active_dev_session=True, dev_proxy_action="OBSERVE"),
    )
    assert pol.decision.value == "OBSERVE"


def test_analyze_incident_with_sysmon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.correlation.proxy_causation.query_sysmon_events", lambda *a, **k: _sysmon_bundle())
    emit_proxy_change_detected_audit(
        tmp_path,
        diff=_transition_row()["diff"],
        attribution=_transition_row()["attribution"],
        decision=_transition_row()["decision"],
    )
    from src.proxy_guard.incident_pipeline import load_latest_proxy_transition

    row = load_latest_proxy_transition(tmp_path)
    assert row is not None
    bundle = analyze_incident_from_row(row, repo_root=tmp_path)
    assert bundle["causation"]["causation_level"] == "FINAL_CAUSATION"
    assert bundle["classification"]["label"] in (
        "REGISTRY_WRITER_CONFIRMED",
        "UNKNOWN_LOCAL_PROXY",
        "KNOWN_DEV_PROXY",
    )
