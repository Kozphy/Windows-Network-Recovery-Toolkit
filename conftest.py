"""Root pytest hooks — fail fast with install instructions when deps are missing."""

from __future__ import annotations

import sys
from pathlib import Path


def _dependency_exit_message(exc: BaseException) -> str:
    repo = Path(__file__).resolve().parent
    venv_python = repo / ".venv" / "Scripts" / "python.exe"
    install_cmd = (
        f"{venv_python} -m pip install -r requirements.txt"
        if venv_python.is_file()
        else "python -m pip install -r requirements.txt"
    )
    pytest_cmd = (
        f"{venv_python} -m pytest -q"
        if venv_python.is_file()
        else "python -m pytest -q"
    )
    repair_cmd = (
        f"{venv_python} -m pip install --force-reinstall --no-cache-dir rpds-py pydantic-core numpy"
        if venv_python.is_file()
        else "python -m pip install --force-reinstall --no-cache-dir rpds-py pydantic-core numpy"
    )

    if isinstance(exc, ModuleNotFoundError):
        missing = getattr(exc, "name", None) or "project dependencies"
        headline = f"Missing dependency {missing!r} (required by backend/db and tests)."
    else:
        headline = "Failed to import project dependencies (often a broken native wheel in .venv)."

    return (
        f"{headline}\n\n"
        f"  Error: {exc}\n"
        f"  Interpreter: {sys.executable}\n\n"
        "Fix (PowerShell, from repo root):\n"
        f"  {install_cmd}\n"
        f"  {pytest_cmd}\n\n"
        "If import still fails after install, repair native wheels:\n"
        f"  {repair_cmd}\n\n"
        "Or run (installs deps then pytest): .\\scripts\\pytest.ps1 -q"
    )


def pytest_configure(config) -> None:
    import pytest

    try:
        import sqlmodel  # noqa: F401
    except (ModuleNotFoundError, ImportError) as exc:
        pytest.exit(_dependency_exit_message(exc), returncode=1)
