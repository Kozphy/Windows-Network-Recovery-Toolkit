"""Registry writer telemetry ingestion and evidence fusion (diagnostic only)."""

from telemetry.models import ProxyTelemetryWindow, RegistryWriteEvent, RegistryWriterEvidence
from telemetry.registry_writer_fusion import (
    default_no_telemetry_evidence,
    fuse_registry_writer_evidence,
)

__all__ = [
    "ProxyTelemetryWindow",
    "RegistryWriteEvent",
    "RegistryWriterEvidence",
    "default_no_telemetry_evidence",
    "fuse_registry_writer_evidence",
]
