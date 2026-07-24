"""Run ``src`` CLI with repo root on sys.path (works with embeddable Python).

Embeddable CPython (``.tools/python312``) uses a ``._pth`` that ignores
``PYTHONPATH``, so ``python -m src`` fails unless the repo root is injected.
Guardian loops and emergency scripts should call this launcher instead of ``-m src``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Preserve ``python scripts/run_src.py <subcommand> ...`` argv shape for argparse.
sys.argv = ["src", *sys.argv[1:]]

from src.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
