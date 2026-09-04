"""Tests for research dataset schema, export, and generators."""

from __future__ import annotations

import json
from pathlib import Path

from research.dataset.export_labels import cases_to_samples, write_labels_csv
from research.dataset.generators import generate_samples
from research.dataset.schema import ResearchSample


def test_research_sample_rejects_bad_failure_id() -> None:
    try:
        ResearchSample(
            sample_id="x",
            scenario_id="y",
            ground_truth_failure="DEAD_PROXY_CONFIG",
            ground_truth_incident_class="DEAD_PROXY_CONFIG",
            expected_action="PREVIEW_ONLY",
            provenance="synthetic_fixture",
        )
        raise AssertionError("expected validation error")
    except Exception as exc:  # noqa: BLE001 — pydantic ValidationError
        assert "F_" in str(exc)


def test_cases_to_samples_cover_v1() -> None:
    samples = cases_to_samples()
    assert len(samples) >= 20
    assert all(s.ground_truth_failure.startswith("F_") for s in samples)
    assert {s.split for s in samples} <= {"development", "held_out"}


def test_write_labels_csv(tmp_path: Path) -> None:
    out = write_labels_csv(tmp_path / "labels.csv")
    text = out.read_text(encoding="utf-8")
    assert "sample_id" in text.splitlines()[0]
    assert "RB-v1-001" in text


def test_generator_deterministic() -> None:
    a = generate_samples(seed=42, count=20)
    b = generate_samples(seed=42, count=20)
    assert [s.model_dump() for s in a] == [s.model_dump() for s in b]
    c = generate_samples(seed=43, count=20)
    assert a[0].sample_id != c[0].sample_id


def test_schema_json_exists() -> None:
    path = Path(__file__).resolve().parents[2] / "research" / "dataset" / "schema.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["$id"] == "research_dataset_sample.v1"
