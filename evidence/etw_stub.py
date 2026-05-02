"""ETW ingestion stub — facade over :mod:`evidence.etw_reader` (no kernel session lifecycle)."""

from __future__ import annotations

from evidence.etw_reader import ETWProviderConfig, ETWReader, ETWTraceBatch, StubETWReader, etw_event_suggests_proxy_writer

__all__ = [
    "ETWProviderConfig",
    "ETWReader",
    "ETWTraceBatch",
    "StubETWReader",
    "etw_event_suggests_proxy_writer",
]
