"""Signal collectors — thin facades over src/proxy_guard and network_agent."""

from .browser_collector import collect_browser_signals
from .dns_collector import collect_dns_signals
from .eventlog_collector import collect_eventlog_signals
from .netstat_collector import collect_netstat_signals
from .process_collector import collect_process_signals
from .proxy_registry_collector import collect_proxy_registry

__all__ = [
    "collect_browser_signals",
    "collect_dns_signals",
    "collect_eventlog_signals",
    "collect_netstat_signals",
    "collect_process_signals",
    "collect_proxy_registry",
]
