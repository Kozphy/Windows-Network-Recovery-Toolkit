"""Fleet-scale contracts — partitioning, deduplication, tenancy, streaming ingestion.

Activate with ``FLEET_MODE=stream``; default ``local`` preserves JSONL for dev/CI.
"""

from platform_core.fleet.deduplication import DedupDecision, IdempotencyStore, InMemoryIdempotencyStore
from platform_core.fleet.ingestion import FleetIngestGateway, IngestResult
from platform_core.fleet.models import FleetEventEnvelope, IdempotencyRecord, TenantContext
from platform_core.fleet.partitioning import PartitionKey, assign_partition, partition_count
from platform_core.fleet.replay import ReplayJobSpec, ReplayCoordinator
from platform_core.fleet.tenancy import TenantIsolationPolicy, assert_tenant_access

__all__ = [
    "DedupDecision",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "FleetIngestGateway",
    "IngestResult",
    "FleetEventEnvelope",
    "IdempotencyRecord",
    "TenantContext",
    "PartitionKey",
    "assign_partition",
    "partition_count",
    "ReplayJobSpec",
    "ReplayCoordinator",
    "TenantIsolationPolicy",
    "assert_tenant_access",
]
