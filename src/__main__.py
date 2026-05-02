"""Entry point for ``python -m src`` (Windows Network Recovery Toolkit decision CLI).

Module responsibility:
    Expose the stdlib-first ``python -m src`` dispatcher implemented in :mod:`src.cli` while preserving identical
    argv parsing and exit-code semantics as invoking ``main()`` directly.

System placement:
    Thin shim only—feature wiring, auditing, and subcommands remain in sibling modules imported by ``cli``.

Side effects:
    None at import time; executing this module invokes :func:`~src.cli.main`, which performs whatever the active
    subparser demands (often subprocess probes and append-only logs).

Raises:
    :class:`SystemExit` with the CLI return code via ``raise SystemExit(main())``.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
