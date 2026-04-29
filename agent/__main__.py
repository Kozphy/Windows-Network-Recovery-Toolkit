"""Allow ``python -m agent`` from repository root."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
