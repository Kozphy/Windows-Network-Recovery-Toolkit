from __future__ import annotations

from platform_core.models import EndpointIdentity
from platform_core.storage import (
    append_jsonl,
    find_by_id,
    iter_jsonl,
    upsert_endpoint,
)


def test_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)

    p = tmp_path / "sample.jsonl"
    append_jsonl(p, {"x": 1})
    rows = list(iter_jsonl(p))
    assert rows == [{"x": 1}]

    upsert_endpoint(EndpointIdentity(endpoint_id="a1", os_family="Win").model_dump())

    endpoints = tmp_path / "endpoints.jsonl"
    assert endpoints.is_file()
    found = find_by_id(endpoints, "endpoint_id", "a1")
    assert found and found.get("endpoint_id") == "a1"

