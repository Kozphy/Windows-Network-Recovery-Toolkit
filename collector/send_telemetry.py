from __future__ import annotations

import argparse
import json
import urllib.request
from typing import Any


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send normalized Windows network telemetry to the risk API."
    )
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/telemetry")
    parser.add_argument("--device-id", default="local-device")
    parser.add_argument("--model", default="xgboost")
    parser.add_argument("--proxy-mismatch", type=int, choices=[0, 1], default=0)
    parser.add_argument("--dns-failure-rate", type=float, default=0.0)
    parser.add_argument("--tls-error-count", type=int, default=0)
    parser.add_argument("--adapter-reset-count", type=int, default=0)
    parser.add_argument("--winhttp-drift", type=int, choices=[0, 1], default=0)
    parser.add_argument(
        "--network-profile",
        choices=["domain", "private", "public"],
        default="private",
    )
    args = parser.parse_args()

    payload = {
        "device_id": args.device_id,
        "model": args.model,
        "proxy_mismatch": args.proxy_mismatch,
        "dns_failure_rate": args.dns_failure_rate,
        "tls_error_count": args.tls_error_count,
        "adapter_reset_count": args.adapter_reset_count,
        "winhttp_drift": args.winhttp_drift,
        "network_profile": args.network_profile,
    }
    result = post_json(args.api, payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
