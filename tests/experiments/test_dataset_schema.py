"""Benchmark dataset schema tests."""

from __future__ import annotations

from experiments.dataset import DEFAULT_DATASET_DIR, load_cases


def test_dataset_v1_minimum_case_count() -> None:
    cases = load_cases(DEFAULT_DATASET_DIR)
    assert len(cases) >= 20


def test_dataset_has_held_out_split() -> None:
    held = load_cases(DEFAULT_DATASET_DIR, split="held_out")
    assert len(held) >= 3


def test_dataset_covers_failure_families() -> None:
    cases = load_cases(DEFAULT_DATASET_DIR)
    families = {c.failure_family for c in cases}
    assert "dead_proxy" in families
    assert "insufficient_data" in families


def test_provenance_categories_present() -> None:
    cases = load_cases(DEFAULT_DATASET_DIR)
    categories = {c.provenance_category for c in cases}
    assert "adversarial_edge_case" in categories
    assert "contradictory_evidence" in categories
