from __future__ import annotations

from src.platform.domains.base import DomainAdapter
from src.platform.domains.cloud import CloudAdapter
from src.platform.domains.infrastructure import InfrastructureAdapter
from src.platform.domains.market import MarketAdapter
from src.platform.domains.security import SecurityAdapter
from src.platform.domains.windows import WindowsAdapter

_ADAPTERS: dict[str, DomainAdapter] = {
    "windows": WindowsAdapter(),
    "security": SecurityAdapter(),
    "cloud": CloudAdapter(),
    "infrastructure": InfrastructureAdapter(),
    "market": MarketAdapter(),
}


def get_adapter(domain: str) -> DomainAdapter:
    key = domain.lower().replace("_", "")
    if key == "marketevents":
        key = "market"
    if key not in _ADAPTERS:
        raise KeyError(domain)
    return _ADAPTERS[key]


def all_adapters() -> list[DomainAdapter]:
    return list(_ADAPTERS.values())
