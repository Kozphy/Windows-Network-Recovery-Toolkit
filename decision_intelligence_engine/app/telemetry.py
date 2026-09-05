from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


def configure_telemetry() -> trace.Tracer:
    if os.getenv("DI_OTEL_ENABLED", "false").lower() == "true":
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": "decision-intelligence-governance-engine",
                    "service.version": "0.3.0",
                }
            )
        )
        trace.set_tracer_provider(provider)
    return trace.get_tracer("decision_intelligence_engine")
