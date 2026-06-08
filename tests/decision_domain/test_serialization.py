from __future__ import annotations

import json

from platform_core.decision_domain import (
    Decision,
    decision_content_digest,
    decision_domain_schema_bundle,
    model_json_schema,
    parse_decision,
    serialize_decision,
)


def test_serialize_decision_deterministic(sample_decision: Decision) -> None:
    first = serialize_decision(sample_decision)
    second = serialize_decision(sample_decision)
    assert first == second
    assert decision_content_digest(sample_decision) == decision_content_digest(sample_decision)


def test_parse_round_trip(sample_decision: Decision) -> None:
    blob = serialize_decision(sample_decision)
    restored = parse_decision(blob)
    assert restored.decision_id == sample_decision.decision_id
    assert serialize_decision(restored) == blob


def test_canonical_json_sorted_keys(sample_decision: Decision) -> None:
    parsed = json.loads(serialize_decision(sample_decision))
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_decision_json_schema_required_fields() -> None:
    schema = model_json_schema(Decision)
    assert schema["title"] == "Decision"
    properties = schema["properties"]
    for field in (
        "decision_id",
        "domain",
        "title",
        "evidence",
        "confidence",
        "risk_score",
        "expected_outcome",
        "alternative_options",
    ):
        assert field in properties, f"missing schema property: {field}"
    required = set(schema.get("required", []))
    assert {
        "domain",
        "title",
        "evidence",
        "confidence",
        "risk_score",
        "expected_outcome",
        "alternative_options",
    } <= required


def test_schema_bundle_includes_all_models() -> None:
    bundle = decision_domain_schema_bundle()
    assert bundle["schema_bundle_version"] == "decision_domain.schema_bundle.v1"
    models = bundle["models"]
    assert set(models) == {
        "Decision",
        "DecisionContext",
        "DecisionEvidence",
        "DecisionExplanation",
        "DecisionOption",
        "DecisionOutcome",
        "DecisionRisk",
    }
    assert models["DecisionOption"]["title"] == "DecisionOption"


def test_fixture_loads_from_disk(fixture_path) -> None:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    decision = parse_decision(raw)
    digest = decision_content_digest(decision)
    assert len(digest) == 64
