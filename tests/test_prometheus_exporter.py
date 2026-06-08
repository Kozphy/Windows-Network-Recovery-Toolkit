from __future__ import annotations

from backend.prometheus_exporter import (
    gauges_from_platform_metrics,
    inc,
    render_prometheus_text,
    reset_metrics_for_tests,
)


def test_render_prometheus_text_includes_counters() -> None:
    reset_metrics_for_tests()
    inc("platform_correlation_runs_total", 2)
    body = render_prometheus_text({"platform_endpoint_count": 5})
    assert "platform_correlation_runs_total 2" in body
    assert "platform_endpoint_count 5" in body


def test_gauges_from_platform_metrics_maps_reliability() -> None:
    gauges = gauges_from_platform_metrics(
        {
            "endpoint_count": 3,
            "reliability_metrics": {"mttr_minutes": 12},
        }
    )
    assert gauges["platform_endpoint_count"] == 3.0
    assert gauges["platform_reliability_mttr_minutes"] == 12.0
