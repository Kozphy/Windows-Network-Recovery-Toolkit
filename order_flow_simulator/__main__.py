"""CLI: python -m order_flow_simulator run --scenario happy_path"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from order_flow_simulator.simulator import OrderFlowSimulator, SCENARIOS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Order-flow reliability simulator (demo).")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="Run a scripted scenario.")
    run_p.add_argument("--scenario", choices=sorted(SCENARIOS), default="happy_path")
    run_p.add_argument("--repo-root", type=Path, default=Path.cwd())
    run_p.add_argument("--order-id", default=None)
    run_p.add_argument("--json", action="store_true")
    replay_p = sub.add_parser("replay", help="Print audit rows for an order id.")
    replay_p.add_argument("order_id")
    replay_p.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    sim = OrderFlowSimulator(repo_root=root)
    if args.command == "run":
        result = sim.run_scenario(args.scenario, order_id=args.order_id)
        if args.json:
            print(json.dumps(result.to_jsonable(), indent=2))
        else:
            print(f"scenario={result.scenario} order_id={result.order_id}")
            print(f"final_state={result.final_state.value} invalid={result.invalid_transition_count}")
            print(f"audit={result.audit_path}")
        return 0
    rows = sim.replay_order(args.order_id)
    print(json.dumps(rows, indent=2))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
