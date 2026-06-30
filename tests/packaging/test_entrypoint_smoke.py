"""Packaging smoke tests — CLI entrypoints without installing background services."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_AGENT = REPO_ROOT / "tests" / "fixtures" / "agent" / "sample_evidence_bundle.json"


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(REPO_ROOT)}


def _run_cli(*args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "windows_network_toolkit", *args],
        cwd=str(REPO_ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def test_version_command_emits_json() -> None:
    result = _run_cli("version")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"]
    assert payload["read_only"] is True
    assert payload["requires_admin"] is False
    assert payload["package"] == "windows-network-recovery-toolkit"


def test_version_matches_pyproject() -> None:
    expected = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    result = _run_cli("version")
    payload = json.loads(result.stdout)
    assert payload["version"] == expected


def test_module_help_lists_version_subcommand() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "windows_network_toolkit", "--help"],
        cwd=str(REPO_ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "version" in result.stdout


def test_principles_explain_read_only_smoke() -> None:
    result = _run_cli("principles", "explain")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "principles" in payload
    assert payload["principles"]


def test_agent_once_fixture_read_only_smoke(tmp_path: Path) -> None:
    spool = tmp_path / "packaging-spool.jsonl"
    result = _run_cli(
        "agent",
        "once",
        "--fixture",
        str(FIXTURE_AGENT),
        "--spool",
        str(spool),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["automatic_repair"] is False
    assert spool.is_file()


def test_backend_module_imports_app() -> None:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(REPO_ROOT)!r}); "
        "from backend.main import app; "
        "assert app is not None"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_wnrt_console_script_if_installed() -> None:
    if shutil.which("wnrt") is None:
        pytest.skip("wnrt console script not on PATH — install with pip/pipx to exercise")
    result = subprocess.run(
        ["wnrt", "version"],
        cwd=str(REPO_ROOT),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"]
