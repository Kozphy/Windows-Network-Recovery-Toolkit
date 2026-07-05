"""Technology-risk persistence — SQLModel engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

_engine = None
_engine_url: str | None = None


def get_database_url() -> str:
    return os.getenv(
        "TRISK_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "sqlite:///./trisk_local.db",
        ),
    )


def reset_engine() -> None:
    """Clear cached engine (tests when TRISK_DATABASE_URL changes)."""
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def get_engine():
    global _engine, _engine_url
    url = get_database_url()
    if _engine is None or _engine_url != url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _engine_url = url
    return _engine


def init_trisk_schema() -> None:
    from backend.db import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session
