"""Entry point for ``python -m src`` (decision-architecture CLI).

Delegates to `src.cli.main` without altering argument parsing behavior.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
