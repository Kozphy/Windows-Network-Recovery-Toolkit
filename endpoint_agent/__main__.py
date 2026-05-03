"""Entry point for ``python -m endpoint_agent``.

Delegates to :func:`endpoint_agent.agent.main` with process ``sys.argv``.

Raises:
    ``SystemExit`` carrying the integer exit code returned by the agent CLI.
"""

from .agent import main

if __name__ == "__main__":
    raise SystemExit(main())
