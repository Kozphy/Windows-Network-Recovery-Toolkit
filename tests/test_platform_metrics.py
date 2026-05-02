from __future__ import annotations

import json

from platform_core.storage import list_metrics


def test_list_metrics_includes_clusters_and_rates(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)

    events_path = tmp_path / "failure_events.jsonl"
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "m1",
                        "endpoint_id": "e1",
                        "status": "open",
                        "category": "proxy",
                        "severity": "medium",
                        "recommended_action_key": "reset_proxy",
                        "first_seen_at": "2026-05-01T12:00:00+00:00",
                        "last_seen_at": "2026-05-01T12:01:00+00:00",
                        "summary": "s",
                    },
                ),
                json.dumps(
                    {
                        "event_id": "m2",
                        "endpoint_id": "e2",
                        "status": "false_positive",
                        "category": "proxy",
                        "severity": "low",
                        "recommended_action_key": "reset_proxy",
                        "first_seen_at": "2026-05-01T12:02:00+00:00",
                        "last_seen_at": "2026-05-01T12:03:00+00:00",
                        "summary": "s",
                    },
                ),
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "endpoints.jsonl").write_text(
        json.dumps({"endpoint_id": "e1"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "remediation_previews.jsonl").write_text("", encoding="utf-8")
    exec_path = tmp_path / "remediation_executions.jsonl"
    exec_path.write_text(
        "\n".join(
            [
                json.dumps({"result": "dry_run"}),
                json.dumps({"result": "success"}),
                json.dumps({"result": "failure"}),
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "audit.jsonl").write_text(
        json.dumps({"decision": "blocked"}) + "\n",
        encoding="utf-8",
    )

    m = list_metrics()
    assert m["endpoint_count"] == 1
    assert m["open_failure_events"] == 1
    assert m["incident_cluster_count"] >= 1
    assert m["affected_endpoint_count"] >= 1
    assert m["dry_run_execution_count"] == 1
    assert m["repair_success_rate"] is not None
    assert m["false_positive_rate"] is not None
