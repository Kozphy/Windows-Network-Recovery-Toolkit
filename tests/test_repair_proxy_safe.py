from __future__ import annotations

import pytest

from src.proxy_guard.remediation import build_user_proxy_disable_mutations
from src.repair.executor import apply_mutations
from src.repair.policy import assert_no_firewall_reset_in_preview


def test_firewall_preview_guard() -> None:
    assert_no_firewall_reset_in_preview("")
    with pytest.raises(ValueError):
        assert_no_firewall_reset_in_preview("run reset_firewall.bat")


def test_apply_mutations_dry_run_returns_zero_codes() -> None:
    mutations, texts = build_user_proxy_disable_mutations(clear_proxy_server_value=False)
    preview = "\n".join(texts)
    assert_no_firewall_reset_in_preview(preview)
    results = apply_mutations(mutations, dry_run=True)
    assert all(r.returncode == 0 for r in results)


def test_clear_server_adds_second_mutation() -> None:
    a, ta = build_user_proxy_disable_mutations(clear_proxy_server_value=False)
    b, tb = build_user_proxy_disable_mutations(clear_proxy_server_value=True)
    assert len(a) == 1
    assert len(b) == 2
    assert "delete" in " ".join(tb).lower()
