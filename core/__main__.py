"""``python -m core`` proxies to ``agent.main``."""

from __future__ import annotations


def main() -> int:
    from agent import main as agent_main

    return agent_main()


if __name__ == "__main__":
    raise SystemExit(main())
