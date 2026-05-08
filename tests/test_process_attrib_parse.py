from __future__ import annotations

from pathlib import Path

from src.attribution.process_tree import parse_simple_process_block


def test_fixture_process_block_roundtrip() -> None:
    blob = Path(__file__).resolve().parent / "fixtures" / "wmic_process_fixture.txt"
    parsed = parse_simple_process_block(blob.read_text(encoding="utf-8"))
    assert parsed["Caption"] == "node.exe"
    assert parsed["ParentProcessId"] == 7580
    assert parsed["CommandLine"] is None
