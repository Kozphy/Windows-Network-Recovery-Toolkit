"""Decision architecture package: ``diagnostics``, ``decision_engine``, ``recommendations``, ``logging``.

Importing this package exposes `SCRIPT_VERSION`; the CLI lives in `src.cli`
and is invoked via ``python -m src``.
"""

from .version import SCRIPT_VERSION

__all__ = ["SCRIPT_VERSION"]
