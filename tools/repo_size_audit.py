#!/usr/bin/env python3
"""Walk a repository tree and report the largest directories and files (stdlib only).

Intended use: pinpoint ``node_modules``, virtualenvs, ``.next``, caches, logs, and packaged artifacts.

Usage::
    python tools/repo_size_audit.py
    python tools/repo_size_audit.py --top 20 --json
    python tools/repo_size_audit.py --include-git

Audit Notes:
    Sizes are naive ``st_size`` sums; sparse files / hard links may distort totals on some filesystems.

Engineering Notes:
    Uses ``Path.resolve()`` so traversal follows symlinks to targets—use with caution if the tree
    contains recursive links (rare for application repos).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Report largest directories and files under a repository root.",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of tools/).",
    )
    p.add_argument(
        "--top",
        type=int,
        default=30,
        metavar="N",
        help="How many largest dirs/files to show (default: 30).",
    )
    p.add_argument(
        "--include-git",
        action="store_true",
        help="Include the .git directory in traversal and totals.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout.",
    )
    return p.parse_args(argv)


def _walk_tree(
    root: Path,
    *,
    include_git: bool,
) -> tuple[dict[Path, int], list[tuple[Path, int]]]:
    """Return (directory_total_bytes, list of (file_path, size)) for all regular files under *root*."""

    dir_totals: dict[Path, int] = defaultdict(int)
    files_out: list[tuple[Path, int]] = []

    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"not a directory: {root}")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        pdir = Path(dirpath)
        if not include_git and ".git" in dirnames:
            dirnames.remove(".git")

        for name in filenames:
            fp = pdir / name
            try:
                st = fp.stat()
            except OSError:
                continue
            if not fp.is_file():
                continue
            size = int(st.st_size)
            files_out.append((fp, size))
            d: Path | None = fp.parent
            while d is not None:
                dir_totals[d] += size
                if d == root:
                    break
                nd = d.parent
                try:
                    nd.relative_to(root)
                except ValueError:
                    break
                d = nd

    return dir_totals, files_out


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        n = n / 1024.0
        if n < 1024.0:
            return f"{n:.2f} {unit}"
    return f"{n:.2f} PiB"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    tools_dir = Path(__file__).resolve().parent
    root = (args.root or tools_dir.parent).resolve()
    top_n = max(1, int(args.top))

    try:
        dir_totals, files = _walk_tree(root, include_git=args.include_git)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    sorted_dirs = sorted(dir_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    sorted_files = sorted(files, key=lambda x: x[1], reverse=True)[:top_n]

    if args.json:
        out = {
            "root": str(root),
            "include_git": args.include_git,
            "top_directories": [
                {"path": str(p.relative_to(root)) if p != root else ".", "bytes": sz}
                for p, sz in sorted_dirs
            ],
            "top_files": [
                {"path": str(p.relative_to(root)), "bytes": sz} for p, sz in sorted_files
            ],
        }
        print(json.dumps(out, indent=2))
        return 0

    print(f"Root: {root}")
    print(f"Exclude .git: {not args.include_git}")
    print()
    print(f"Top {top_n} directories by total file size (descending):")
    for p, sz in sorted_dirs:
        rel = "." if p == root else p.relative_to(root).as_posix()
        print(f"  {_format_bytes(sz):>12}  {rel}")
    print()
    print(f"Top {top_n} largest files:")
    for p, sz in sorted_files:
        print(f"  {_format_bytes(sz):>12}  {p.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
