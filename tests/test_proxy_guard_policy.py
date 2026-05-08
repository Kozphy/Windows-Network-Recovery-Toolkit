from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.proxy_guard.policy import load_proxy_guard_policy


def test_load_policy_and_substring_match(tmp_path: Path) -> None:
    p = tmp_path / "pol.json"
    p.write_text(
        json.dumps(
            {
                "allowed_process_name_substrings": ["good"],
                "allowed_process_names_exact": [],
                "allow_when_attribution_empty": False,
            },
        ),
        encoding="utf-8",
    )
    pol = load_proxy_guard_policy(p)
    d = pol.evaluate([{"process_name": "GOODAPP.exe", "pid": 1}])
    assert d.allowed
    assert d.matched_rule is not None
    d2 = pol.evaluate([{"process_name": "malware.exe", "pid": 2}])
    assert not d2.allowed


def test_empty_owners_default_deny(tmp_path: Path) -> None:
    p = tmp_path / "pol.json"
    p.write_text("{}", encoding="utf-8")
    pol = load_proxy_guard_policy(p)
    assert not pol.evaluate([]).allowed


def test_allow_when_attribution_empty(tmp_path: Path) -> None:
    p = tmp_path / "pol.json"
    p.write_text(
        json.dumps({"allow_when_attribution_empty": True}),
        encoding="utf-8",
    )
    pol = load_proxy_guard_policy(p)
    assert pol.evaluate([]).allowed


def test_exact_match_wins_before_substrings(tmp_path: Path) -> None:
    p = tmp_path / "pol.json"
    p.write_text(
        json.dumps({"allowed_process_names_exact": ["allowed.exe"]}),
        encoding="utf-8",
    )
    pol = load_proxy_guard_policy(p)
    assert pol.evaluate([{"process_name": "allowed.exe"}]).allowed


def test_invalid_policy_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        load_proxy_guard_policy(bad)
