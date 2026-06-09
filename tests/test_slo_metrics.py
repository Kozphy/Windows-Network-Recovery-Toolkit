"""SLO metrics tests — fixture JSONL only."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from platform_core.reliability_metrics import compute_slo_metrics, slo_metrics_dict

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "platform_slo"


def _seed_platform_data(tmp_path: Path) -> None:
    for name in (
        "platform_signals.jsonl",
        "failure_events.jsonl",
        "audit.jsonl",
        "remediation_previews.jsonl",
    ):
        shutil.copy(FIXTURE_DIR / name, tmp_path / name)


def test_compute_slo_metrics_from_fixtures(tmp_path) -> None:
    _seed_platform_data(tmp_path)
    slo = compute_slo_metrics(data_root=tmp_path)
    assert slo.proxy_drift_incidents_total >= 2
    assert slo.remediation_preview_count == 1
    assert slo.blocked_high_risk_action_count >= 1
    assert slo.mean_time_to_detect_seconds is not None
    assert slo.mean_time_to_explain_seconds is not None
    assert 0.0 <= slo.proof_unavailable_rate <= 1.0
    assert 0.0 <= slo.final_causation_rate <= 1.0


def test_slo_metrics_dict_serializable(tmp_path) -> None:
    _seed_platform_data(tmp_path)
    blob = slo_metrics_dict(data_root=tmp_path)
    json.dumps(blob)
    assert "reliability" in blob


def test_platform_slo_route(monkeypatch, tmp_path) -> None:
    _seed_platform_data(tmp_path)
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.reliability_metrics.platform_data_dir", lambda: tmp_path)
    from backend.platform_routes import platform_slo
    from platform_core.rbac import DemoPrincipal

    principal = DemoPrincipal(operator_id="pytest", role="viewer")
    body = platform_slo(principal=principal)
    assert body["proxy_drift_incidents_total"] >= 2
