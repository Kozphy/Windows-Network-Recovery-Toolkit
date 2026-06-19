"""Package entrypoint for ``python -m windows_network_toolkit``.

Delegates to ``cli.main`` with prog name ``windows_network_toolkit`` for argparse help text.
"""

from windows_network_toolkit.cli import main

if __name__ == "__main__":
    raise SystemExit(main(prog="windows_network_toolkit"))
