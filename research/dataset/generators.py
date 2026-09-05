"""Deterministic synthetic research-sample generator (scale-out scaffolding).

Generates anonymized feature records with independent ground-truth labels.
Does not call live Windows APIs or external network services.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from research.dataset.schema import ResearchSample
from research.taxonomy import load_taxonomy

# Stable scenario templates — labels chosen independently of any detector.
_TEMPLATES: tuple[tuple[str, str, str, bool], ...] = (
    ("dead_localhost_proxy", "DEAD_PROXY_CONFIG", "PREVIEW_ONLY", True),
    ("stack_mismatch", "WININET_WINHTTP_MISMATCH", "PREVIEW_ONLY", True),
    ("direct_ok", "DIRECT_OK", "NONE", False),
    ("insufficient", "ERROR_INSUFFICIENT_DATA", "PREVIEW_ONLY", False),
    ("ipv6_partial", "IPV6_BROKEN_IPV4_OK", "PREVIEW_ONLY", True),
)


def generate_samples(*, seed: int, count: int) -> list[ResearchSample]:
    if count < 1:
        raise ValueError("count must be >= 1")
    rng = random.Random(seed)
    tax = load_taxonomy()
    samples: list[ResearchSample] = []
    for index in range(count):
        scenario_key, incident, action, repairable = _TEMPLATES[index % len(_TEMPLATES)]
        failure_ids = tax.ids_for_incident_class(incident)
        failure_id = failure_ids[0]
        proxy_enabled = scenario_key in {"dead_localhost_proxy", "stack_mismatch"}
        listener = scenario_key == "dead_localhost_proxy" and rng.random() < 0.3
        samples.append(
            ResearchSample(
                sample_id=f"SYN-{seed:04d}-{index:04d}",
                scenario_id=f"SYN-SCENARIO-{scenario_key}",
                os_version_category=rng.choice(["windows_10", "windows_11", "unspecified_fixture"]),
                evidence_features={
                    "proxy_enabled": proxy_enabled,
                    "listener_present": listener,
                    "direct_probe_ok": scenario_key in {"direct_ok", "ipv6_partial"},
                    "dns_ok": scenario_key != "insufficient",
                    "scenario_key": scenario_key,
                },
                ground_truth_failure=failure_id,
                ground_truth_incident_class=incident,
                severity="labeled",
                compound_failure=False,
                expected_action=action,
                repairable=repairable,
                provenance="synthetic_generated",
                generation_seed=seed,
                split="synthetic_generated",
                limitations=["generator_v1_coarse_features"],
            )
        )
    return samples


def write_jsonl(samples: list[ResearchSample], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(sample.model_dump_json() + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic research samples"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("research/dataset/processed/synthetic_smoke.jsonl"),
    )
    args = parser.parse_args(argv)
    samples = generate_samples(seed=args.seed, count=args.count)
    write_jsonl(samples, args.out)
    # Determinism check payload for operators
    digest_source = "".join(s.sample_id for s in samples)
    print(
        json.dumps(
            {
                "status": "ok",
                "count": len(samples),
                "seed": args.seed,
                "out": str(args.out),
                "id_concat_len": len(digest_source),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
