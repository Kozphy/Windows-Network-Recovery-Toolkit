"""Generate a deterministic controlled telemetry dataset for benchmark smoke tests.

This dataset is synthetic by design. It validates the research pipeline and CI only;
it must never be presented as evidence of real-world detection quality.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42


def generate(rows: int) -> pd.DataFrame:
    if rows < 100:
        raise ValueError("Controlled research dataset requires at least 100 rows")
    rng = np.random.default_rng(RANDOM_STATE)
    observed_at = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    proxy_mismatch = rng.binomial(1, 0.22, rows)
    winhttp_drift = rng.binomial(1, 0.18, rows)
    tls_error_count = rng.poisson(0.7, rows)
    dns_failure_rate = np.clip(rng.beta(1.5, 8.0, rows), 0, 1)
    adapter_reset_count = rng.poisson(0.35, rows)
    network_profile = rng.choice(["domain", "private", "public"], rows, p=[0.45, 0.4, 0.15])

    latent = (
        1.8 * proxy_mismatch
        + 1.5 * winhttp_drift
        + 0.45 * tls_error_count
        + 3.0 * dns_failure_rate
        + 0.35 * adapter_reset_count
        + (network_profile == "public") * 0.5
        + rng.normal(0, 0.9, rows)
        - 2.1
    )
    probability = 1.0 / (1.0 + np.exp(-latent))
    failure_label = rng.binomial(1, probability)

    return pd.DataFrame(
        {
            "observed_at": observed_at,
            "proxy_mismatch": proxy_mismatch,
            "dns_failure_rate": dns_failure_rate,
            "tls_error_count": tls_error_count,
            "adapter_reset_count": adapter_reset_count,
            "winhttp_drift": winhttp_drift,
            "network_profile": network_profile,
            "failure_label": failure_label,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic controlled telemetry")
    parser.add_argument("--rows", type=int, default=600)
    parser.add_argument("--out", default="research/data/controlled_telemetry.csv")
    args = parser.parse_args()
    frame = generate(args.rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    print(f"wrote {len(frame)} controlled rows to {out}")


if __name__ == "__main__":
    main()
