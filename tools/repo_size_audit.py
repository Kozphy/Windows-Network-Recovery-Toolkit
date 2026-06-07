#!/usr/bin/env python3
"""Report repository size and largest tracked-path candidates (read-only)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n //= 1024
    return f"{n:.1f}TB"


def scan(root: Path, *, top: int) -> list[tuple[int, Path]]:
    sizes: list[tuple[int, Path]] = []
    skip = {".git", "node_modules", ".next", ".venv", "__pycache__", ".pytest_cache"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                sizes.append((p.stat().st_size, p))
            except OSError:
                continue
    sizes.sort(reverse=True, key=lambda x: x[0])
    return sizes[:top]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit repo file sizes (local hygiene check).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args(argv)

    rows = scan(args.root.resolve(), top=args.top)
    total = sum(size for size, _ in rows)
    print(f"Top {len(rows)} files under {args.root} (excluding common generated dirs):")
    for size, path in rows:
        rel = path.relative_to(args.root)
        print(f"  {_human(size):>8}  {rel}")
    print(f"\nSum of listed files: {_human(total)}")
    print("See docs/repository_hygiene.md for cleanup guidance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
