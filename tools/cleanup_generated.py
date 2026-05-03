#!/usr/bin/env python3
"""Dry-run-first cleanup of generated artifacts and dependency trees (stdlib only).

Removes only paths deemed safe: caches, virtualenv folders, Next.js output, lockstep runtime dirs at
repository root, and stray artifact extensions. Source trees under ``docs/``, ``tests/``, ``src/``,
etc. are skipped except for explicit generated markers (``__pycache__``, bytecode).

Usage::
    python tools/cleanup_generated.py           # dry-run: print candidates only
    python tools/cleanup_generated.py --apply   # delete after interactive confirmation
    python tools/cleanup_generated.py --apply --yes   # skip confirmation (CI/automation)

Safety:
    Run from repository root. Review dry-run output before ``--apply``.

Audit Notes:
    Deletions are local filesystem only; there is no audit log file—capture stdout if you need evidence.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from pathlib import Path

# Source prefixes: allow narrowly-scoped artifact deletes (bytecode caches) beneath these.
_PROTECTED_SOURCE_PREFIXES = (
    "src/",
    "backend/",
    "platform_core/",
    "endpoint_agent/",
    "failure_system/",
)

# Never delete *anything* beneath these trees (fixtures, scripted tooling, authored docs).
_NO_TOUCH_PREFIXES_POSIX = ("docs/", "tests/", "examples/", "scripts/")

_APPLY_WARNING = """\
================================================================================
WARNING: --apply will permanently delete files and directories on disk.
Review the dry-run list above. This cannot be undone except from backups or VCS.
================================================================================
"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Remove generated artifacts (dry-run by default). "
            "Deletes node_modules, caches, root runtime dirs, and matching file extensions "
            "outside protected source trees."
        ),
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of tools/).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Perform deletions (still requires typing 'yes' unless --yes).",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="With --apply, skip interactive confirmation (use only in automation).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print skip/protect decisions in addition to deletion candidates.",
    )
    return p.parse_args(argv)


def _rel_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_no_touch(rel_posix: str) -> bool:
    """True for docs/tests/examples/scripts — no generated cleanup inside these trees."""

    for prefix in _NO_TOUCH_PREFIXES_POSIX:
        if rel_posix == prefix.rstrip("/") or rel_posix.startswith(prefix):
            return True
    return False


def _is_frontend_exception(rel_posix: str) -> bool:
    return rel_posix == "frontend/node_modules" or rel_posix.startswith("frontend/node_modules/") or (
        rel_posix == "frontend/.next" or rel_posix.startswith("frontend/.next/")
    )


def _is_under_frontend(rel_posix: str) -> bool:
    return rel_posix == "frontend" or rel_posix.startswith("frontend/")


def _is_protected_tree(rel_posix: str) -> bool:
    """True inside backend/src packages and frontend (excluding allowlisted frontend artifacts)."""

    if _is_frontend_exception(rel_posix):
        return False
    if _is_under_frontend(rel_posix):
        return True
    for prefix in _PROTECTED_SOURCE_PREFIXES:
        if rel_posix == prefix.rstrip("/") or rel_posix.startswith(prefix):
            return True
    return False


def _generated_dir_segment(name: str) -> bool:
    return name in {
        "node_modules",
        ".venv",
        "venv",
        ".next",
        "dist",
        "build",
        ".cache",
        ".pytest_cache",
        "htmlcov",
        "coverage",
        "__pycache__",
    }


def _root_runtime_dir(name: str) -> bool:
    return name in {"logs", "reports", "platform_data", "evidence"}


def _dir_may_delete(rel_posix: str, dirname: str, _root: Path, _full_path: Path) -> bool:
    """Whether the directory *full_path* (basename *dirname*) may be removed entirely."""

    if _is_no_touch(rel_posix):
        return False

    parts = rel_posix.split("/")

    if dirname in {"__pycache__", ".pytest_cache"}:
        return True

    if dirname in {"htmlcov", "coverage", ".cache"} and not _is_protected_tree(rel_posix):
        return True

    if _is_protected_tree(rel_posix):
        if dirname == "node_modules" and _is_frontend_exception(rel_posix):
            return True
        if dirname == ".next" and _is_frontend_exception(rel_posix):
            return True
        return False

    if len(parts) == 1 and _root_runtime_dir(dirname):
        return True

    if _generated_dir_segment(dirname):
        # e.g. repo-root or tooling node_modules, .venv — not under protected tree.
        return True

    return False


_FILE_GLOBS = (
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.jsonl",
    "*.sqlite",
    "*.db",
    "*.parquet",
    "*.zip",
    "*.7z",
    "*.tar",
    "*.gz",
    "*.exe",
    "*.msi",
)


def _file_may_delete(rel_posix: str, root: Path, path: Path) -> bool:
    if _is_no_touch(rel_posix):
        return False
    name = path.name
    if any(fnmatch.fnmatch(name, pat) for pat in _FILE_GLOBS):
        if path.suffix.lower() in {".pyc", ".pyo"}:
            return True
        if "__pycache__" in rel_posix.split("/"):
            return True
        return not _is_protected_tree(rel_posix)
    return False


def _collect_dir_targets(root: Path, *, verbose: bool) -> list[Path]:
    root = root.resolve()
    targets: list[Path] = []

    for dirpath, dirnames, _filenames in os.walk(root, topdown=True, followlinks=False):
        if ".git" in dirnames:
            dirnames.remove(".git")
        p = Path(dirpath).resolve()
        if ".git" in p.parts:
            continue
        try:
            rel = _rel_posix(p, root)
        except ValueError:
            continue
        dirname = p.name
        if dirname == ".git":
            continue
        if _dir_may_delete(rel, dirname, root, p):
            if verbose:
                print(f"[dir-candidate] {rel}", file=sys.stderr)
            targets.append(p)
        elif verbose:
            print(f"[dir-skip] {rel}", file=sys.stderr)

    return _outermost_dirs(targets)


def _outermost_dirs(paths: list[Path]) -> list[Path]:
    """Prefer deleting parent trees once: drop child dirs already covered by a selected ancestor."""

    s = sorted({p.resolve() for p in paths}, key=lambda x: len(x.parts))
    out: list[Path] = []
    for p in s:
        if any(p.is_relative_to(o) for o in out):
            continue
        out.append(p)
    return sorted(out, key=lambda x: len(x.parts), reverse=True)


def _collect_file_targets(root: Path, dirs_to_remove: set[Path], *, verbose: bool) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        if ".git" in dirnames:
            dirnames.remove(".git")
        pdir = Path(dirpath)
        if ".git" in pdir.parts:
            continue
        try:
            rel_dir = _rel_posix(pdir, root)
        except ValueError:
            continue
        for fn in filenames:
            fp = pdir / fn
            if not fp.is_file():
                continue
            try:
                rel = _rel_posix(fp, root)
            except ValueError:
                continue
            if any(fp.is_relative_to(d) for d in dirs_to_remove):
                continue
            if _file_may_delete(rel, root, fp):
                if verbose:
                    print(f"[file-candidate] {rel}", file=sys.stderr)
                files.append(fp)
            elif verbose:
                print(f"[file-skip] {rel}", file=sys.stderr)
    return files


def _delete_paths(dirs: list[Path], files: list[Path]) -> tuple[int, int]:
    """Perform deletions; return (dirs_removed, files_removed) counts."""

    d_count = 0
    f_count = 0
    for f in files:
        try:
            f.unlink()
            f_count += 1
        except OSError as e:
            print(f"error unlink {f}: {e}", file=sys.stderr)
    for d in dirs:
        try:
            shutil.rmtree(d, ignore_errors=False)
            d_count += 1
        except OSError as e:
            print(f"error rmtree {d}: {e}", file=sys.stderr)
    return d_count, f_count


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = (args.root or _repo_root()).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    dirs = _collect_dir_targets(root, verbose=args.verbose)
    dir_set = {d.resolve() for d in dirs}
    files = _collect_file_targets(root, dir_set, verbose=args.verbose)

    print(f"Root: {root}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN (no changes)'}")
    print(f"Directory candidates: {len(dirs)}")
    print(f"File candidates: {len(files)}")
    print()

    for f in files:
        print(f"FILE {f}")
    for d in dirs:
        print(f"DIR  {d}")
    print()

    if not args.apply:
        print("Dry-run only. Re-run with --apply to delete (after confirmation).")
        return 0

    print(_APPLY_WARNING, file=sys.stderr)
    if not args.yes:
        try:
            confirm = input("Type 'yes' to delete: ").strip()
        except EOFError:
            confirm = ""
        if confirm.lower() != "yes":
            print("Aborted.")
            return 3

    d_count, f_count = _delete_paths(dirs, files)
    print(f"Removed {d_count} director(y/ies) and {f_count} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
