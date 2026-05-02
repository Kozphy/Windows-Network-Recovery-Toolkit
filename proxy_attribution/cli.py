"""Console entry for the Proxy Attribution Engine (read-only JSON to stdout)."""

from __future__ import annotations

import json
import sys

from proxy_attribution.attribution_engine import run_attribution


def main(argv: list[str] | None = None) -> int:
    """Print attribution JSON. Unknown CLI flags are ignored for forward compatibility."""

    _ = argv  # reserved
    print(json.dumps(run_attribution(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
