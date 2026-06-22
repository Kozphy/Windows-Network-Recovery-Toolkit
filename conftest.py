"""Root pytest hooks — fail fast with install instructions when deps are missing."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure(config) -> None:
    try:
        import sqlmodel  # noqa: F401
    except ModuleNotFoundError:
        import pytest

        repo = Path(__file__).resolve().parent
        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        venv_hint = (
            f"  {venv_python} -m pip install -r requirements.txt\n"
            f"  {venv_python} -m pytest -q\n"
            if venv_python.is_file()
            else "  python -m pip install -r requirements.txt\n"
            "  python -m pytest -q\n"
        )
        msg = (
            "Missing dependency 'sqlmodel' (required by backend/db).\n\n"
            "pytest is not using an environment with project dependencies installed.\n"
            f"  Current interpreter: {sys.executable}\n\n"
            "Fix (PowerShell, from repo root):\n"
            "  pip install -r requirements.txt\n"
            "  pytest -q\n\n"
            "Or use the project virtualenv:\n"
            f"{venv_hint}\n"
            "Or run: .\\scripts\\pytest.ps1 -q"
        )
        pytest.exit(msg, returncode=1)
