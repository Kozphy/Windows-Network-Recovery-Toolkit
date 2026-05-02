"""Executable module shim delegating to ``failure_system.cli``.

Side effects:
    Determined entirely by the invoked subcommand (diagnose/search/recommend).

See Also:
    ``python -m failure_system --help`` for argument surfaces preserved verbatim.
"""

from __future__ import annotations

from failure_system.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
