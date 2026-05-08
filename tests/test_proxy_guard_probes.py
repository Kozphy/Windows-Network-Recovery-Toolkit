from __future__ import annotations

from src.core.models import ProxyRegistrySnapshot
from src.proxy_guard.config import ProbeRetrySettings
from src.proxy_guard.probes import read_proxy_registry_with_retries, snapshot_totally_unreadable


def test_snapshot_totally_unreadable() -> None:
    s = ProxyRegistrySnapshot(None, None, None, None)
    assert snapshot_totally_unreadable(s) is True
    s2 = ProxyRegistrySnapshot(0, None, None, None)
    assert snapshot_totally_unreadable(s2) is False


def test_read_retries_until_partial_success() -> None:
    good = ProxyRegistrySnapshot(0, None, None, 0)
    bad = ProxyRegistrySnapshot(None, None, None, None)
    calls = {"n": 0}

    def side_effect(*_a: object, **_k: object) -> ProxyRegistrySnapshot:
        calls["n"] += 1
        return bad if calls["n"] < 2 else good

    # Patch read inside probes module
    import src.proxy_guard.probes as probes

    orig = probes.read_proxy_registry

    def fake_read(**kwargs: object) -> ProxyRegistrySnapshot:
        return side_effect()

    probes.read_proxy_registry = fake_read  # type: ignore[method-assign]
    try:
        snap, notes = read_proxy_registry_with_retries(
            run=lambda *_a, **_k: None,
            settings=ProbeRetrySettings(max_attempts=3, backoff_seconds=0.0),
            sleep_fn=lambda _x: None,
        )
        assert snap.proxy_enable == 0
        assert any("recovered" in n for n in notes)
    finally:
        probes.read_proxy_registry = orig  # type: ignore[method-assign]
