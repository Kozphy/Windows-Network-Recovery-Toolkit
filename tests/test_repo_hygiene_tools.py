"""Smoke tests for ``tools/repo_size_audit.py`` and ``tools/cleanup_generated.py``."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "tools" / "repo_size_audit.py"
CLEANUP = REPO / "tools" / "cleanup_generated.py"


def _run(script: Path, args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd or REPO),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def test_repo_size_audit_excludes_dot_git_by_default(tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    (root / ".git").mkdir()
    (root / ".git" / "blob.bin").write_bytes(b"z" * 50_000)
    (root / "tracked.txt").write_text("a", encoding="utf-8")

    res = _run(AUDIT, ["--root", str(root), "--top", "5", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    paths = {f["path"] for f in data["top_files"]}
    assert "tracked.txt" in paths
    assert not any(p.startswith(".git") for p in paths)


def test_repo_size_audit_include_git(tmp_path: Path) -> None:
    root = tmp_path / "r2"
    root.mkdir()
    (root / ".git").mkdir()
    (root / ".git" / "big.bin").write_bytes(b"x" * 20_000)

    res = _run(AUDIT, ["--root", str(root), "--top", "5", "--json", "--include-git"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    paths = {f["path"] for f in data["top_files"]}
    assert any(".git" in p for p in paths)


def test_cleanup_generated_dry_run_does_not_delete(tmp_path: Path) -> None:
    root = tmp_path / "r3"
    root.mkdir()
    victim = root / "logs" / "n.log"
    victim.parent.mkdir()
    victim.write_text("keep", encoding="utf-8")

    res = _run(CLEANUP, ["--root", str(root)])
    assert res.returncode == 0, res.stderr
    assert "DRY-RUN" in res.stdout
    assert victim.is_file()


def test_cleanup_generated_apply_removes_root_logs(tmp_path: Path) -> None:
    root = tmp_path / "r3b"
    root.mkdir()
    victim = root / "logs" / "n.log"
    victim.parent.mkdir()
    victim.write_text("gone", encoding="utf-8")

    res_apply = _run(CLEANUP, ["--root", str(root), "--apply", "--yes"])
    assert res_apply.returncode == 0, res_apply.stderr
    assert not victim.is_file()


def test_cleanup_generated_never_touches_core_source_logs(tmp_path: Path) -> None:
    """`core/` is protected; *.log paths there must survive apply."""

    root = tmp_path / "r4"
    root.mkdir()
    src_log = root / "core" / "noise.log"
    src_log.parent.mkdir(parents=True)
    src_log.write_text("core-log", encoding="utf-8")
    victim = root / "logs" / "root.log"
    victim.parent.mkdir(parents=True)
    victim.write_text("root-log", encoding="utf-8")

    res = _run(CLEANUP, ["--root", str(root), "--apply", "--yes"])
    assert res.returncode == 0, res.stderr
    assert src_log.is_file()
    assert not victim.is_file()


def test_cleanup_generated_allows_frontend_node_modules(tmp_path: Path) -> None:
    root = tmp_path / "r5"
    root.mkdir()
    nm = root / "frontend" / "node_modules" / "pkg" / "x.js"
    nm.parent.mkdir(parents=True)
    nm.write_text("//", encoding="utf-8")

    res = _run(CLEANUP, ["--root", str(root), "--apply", "--yes"])
    assert res.returncode == 0, res.stderr
    assert not nm.exists()


def test_cleanup_generated_no_touch_tests_tree(tmp_path: Path) -> None:
    root = tmp_path / "r6"
    root.mkdir()
    fixture = root / "tests" / "__pycache__" / "dummy.pyc"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"\0\0")

    res = _run(CLEANUP, ["--root", str(root), "--apply", "--yes"])
    assert res.returncode == 0, res.stderr
    assert fixture.is_file()

