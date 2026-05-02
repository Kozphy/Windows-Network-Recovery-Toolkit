from __future__ import annotations

from unittest.mock import patch

from endpoint_agent.agent import run_cycle


def test_run_cycle_skips_http_when_skip_http(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    with patch("endpoint_agent.agent.collect_endpoint_cycle") as mc:
        mc.return_value = {
            "endpoint_snapshot": {
                "endpoint_id": "e1",
                "network_state": {},
                "proxy_state": {},
                "dns_state": {},
                "tcp_state": {},
                "browser_path_state": {},
                "process_clues": {},
                "raw_data_redacted": True,
            },
            "failure_event": {
                "event_id": "f1",
                "endpoint_id": "e1",
                "severity": "low",
                "category": "unknown",
                "confidence": 0.25,
                "summary": "mock",
                "recommended_action_key": "inspect_proxy",
                "failure_block_id": "",
            },
            "failure_block_id": "fb-nonempty-mark",
            "top_hypothesis": "mock",
            "confidence": 0.25,
        }
        with patch("endpoint_agent.agent.post_json_with_retry") as post:
            out = run_cycle(base_api="http://127.0.0.1:8000", skip_http=True)
            assert post.call_count == 0
            assert out["automatic_repair"] is False

