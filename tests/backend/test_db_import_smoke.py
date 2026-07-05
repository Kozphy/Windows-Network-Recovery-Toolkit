"""Smoke test: backend DB layer imports without optional extras."""

from __future__ import annotations


def test_backend_db_imports():
    from backend.db import get_engine, init_trisk_schema, reset_engine

    assert callable(init_trisk_schema)
    assert callable(reset_engine)
    assert get_engine() is not None
