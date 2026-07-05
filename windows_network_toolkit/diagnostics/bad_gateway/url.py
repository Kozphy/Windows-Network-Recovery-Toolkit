"""URL parsing for bad-gateway diagnostics.

Module responsibility:
    Parse http/https target URL into host, port, scheme for probe routing.

Raises:
    ValueError: When scheme is not http/https or host is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedTarget:
    url: str
    scheme: str
    host: str
    port: int


def parse_target(url: str) -> ParsedTarget:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must include a host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return ParsedTarget(url=url.strip(), scheme=parsed.scheme, host=host, port=port)
