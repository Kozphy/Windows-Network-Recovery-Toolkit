from __future__ import annotations

import json
from pathlib import Path

from app.agent import AgentOrchestrator
from app.models import AgentRequest


def main() -> int:
    agent = AgentOrchestrator()
    cases = [json.loads(line) for line in Path("evals/cases.json").read_text().splitlines() if line.strip()]
    passed = 0

    for case in cases:
        result = agent.handle(AgentRequest(message=case["input"]))
        action = result.proposed_action
        actual_tool = action.tool.name if action else None
        actual_approval = action.requires_approval if action else None
        ok = (
            actual_tool == case["expected_tool"]
            and actual_approval == case["requires_approval"]
            and len(result.evidence) >= case["min_evidence"]
        )
        passed += int(ok)
        print(json.dumps({"input": case["input"], "passed": ok, "actual_tool": actual_tool}))

    score = passed / len(cases) if cases else 0.0
    print(json.dumps({"metric": "agent_regression_pass_rate", "score": score, "passed": passed, "total": len(cases)}))
    return 0 if score == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
