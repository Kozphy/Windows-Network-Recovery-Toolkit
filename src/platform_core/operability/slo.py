"""SLO measurement placeholders."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass
class SLOSnapshot:
    diagnosis_latency_p95_ms: float = 0.0
    policy_evaluation_p99_ms: float = 0.0
    audit_write_success_rate: float = 1.0
    replay_certification_success_rate: float = 1.0
    outcome_recording_success_rate: float = 1.0
    samples: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_latency_p95_ms": self.diagnosis_latency_p95_ms,
            "policy_evaluation_p99_ms": self.policy_evaluation_p99_ms,
            "audit_write_success_rate": self.audit_write_success_rate,
            "replay_certification_success_rate": self.replay_certification_success_rate,
            "outcome_recording_success_rate": self.outcome_recording_success_rate,
            "samples": self.samples,
        }


class SLOTimer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self._start) * 1000.0
