"""Tests for ai-eval CLI command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from windows_network_toolkit.cli import cmd_ai_eval

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "ai_evals" / "support_bot_cases.json"


class _Args:
    cases = str(FIXTURE)
    format = "json"


def test_cmd_ai_eval_json_exit_zero(capsys) -> None:
    rc = cmd_ai_eval(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["schema_version"] == "ai_evals.v1"
    assert data["total_cases"] == 8


def test_cmd_ai_eval_markdown(capsys) -> None:
    args = _Args()
    args.format = "markdown"
    rc = cmd_ai_eval(args)
    assert rc == 0
    assert "AI Evals Feedback Loop Report" in capsys.readouterr().out


def test_cli_subprocess_module_invocation() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "windows_network_toolkit",
            "ai-eval",
            "--cases",
            str(FIXTURE),
            "--format",
            "json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(ROOT)},
    )
    assert proc.returncode == 0, proc.stderr
    assert "ai_evals.v1" in proc.stdout
