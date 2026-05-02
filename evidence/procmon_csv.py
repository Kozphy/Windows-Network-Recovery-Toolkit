"""Procmon CSV → structured registry-write rows — thin facade over :mod:`evidence.procmon_importer`.

Import this module name in interviews/tests when describing the Procmon ingestion boundary explicitly.
"""

from __future__ import annotations

from evidence.procmon_importer import ProcmonRegistryWrite, iter_procmon_registry_writes_from_csv, procmon_concerns_proxy

__all__ = [
    "ProcmonRegistryWrite",
    "iter_procmon_registry_writes_from_csv",
    "procmon_concerns_proxy",
]
