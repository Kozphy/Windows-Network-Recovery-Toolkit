"""OpenTelemetry tracing with optional Azure Monitor export.

Local development keeps the existing console exporter behavior. Azure export is
opt-in: set ``WNRT_AZURE_MONITOR_ENABLED=1`` and provide
``APPLICATIONINSIGHTS_CONNECTION_STRING``. If the Azure Monitor distro is not
installed, tracing degrades gracefully instead of blocking the API startup.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_tracer: Any = None
_otel_available = False
_azure_monitor_configured = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    _otel_available = True
except ImportError:
    trace = None  # type: ignore[assignment,misc]


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _configure_azure_monitor() -> bool:
    """Configure Azure Monitor OpenTelemetry when explicitly enabled.

    Returns ``True`` only when the Azure Monitor distro was successfully
    configured. The Application Insights connection string is never logged.
    """
    global _azure_monitor_configured

    if not _env_flag("WNRT_AZURE_MONITOR_ENABLED"):
        return False

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()
    if not connection_string:
        logger.warning(
            "Azure Monitor tracing requested but APPLICATIONINSIGHTS_CONNECTION_STRING is unset; "
            "continuing without Azure export."
        )
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        logger.warning(
            "Azure Monitor tracing requested but azure-monitor-opentelemetry is not installed; "
            "install the azure optional dependency or requirements-azure.txt."
        )
        return False

    configure_azure_monitor(connection_string=connection_string)
    _azure_monitor_configured = True
    logger.info("Azure Monitor OpenTelemetry export enabled for WNRT.")
    return True


def init_tracing(service_name: str = "endpoint-reliability-platform") -> bool:
    """Initialize tracing with Azure Monitor or the local console exporter.

    Azure Monitor is preferred only when explicitly enabled. Otherwise the
    existing console exporter remains the default development behavior.
    """
    global _tracer, _otel_available

    if not _otel_available or trace is None:
        return False

    if _configure_azure_monitor():
        _tracer = trace.get_tracer(service_name)
        return True

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    return True


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """Create a span or no-op when OpenTelemetry is unavailable."""
    if _tracer is None:
        yield
        return
    with _tracer.start_as_current_span(name) as active_span:
        for key, value in attributes.items():
            active_span.set_attribute(key, str(value))
        yield


def get_trace_id() -> str | None:
    """Return the active W3C trace id as a 32-character hex string, if any."""
    if not _otel_available or trace is None:
        return None
    active_span = trace.get_current_span()
    ctx = active_span.get_span_context()
    if ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None


def azure_monitor_configured() -> bool:
    """Expose configuration state for health checks and tests without secrets."""
    return _azure_monitor_configured
