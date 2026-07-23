# Repository Agent Harness

This directory defines a bounded, auditable loop for repository-level automation.

## Loop

`observe -> propose -> policy gate -> execute in sandbox -> verify -> score -> audit -> stop/escalate`

The harness is intentionally conservative:

- read-only observation by default;
- no registry, firewall, process, credential, or network mutation without explicit approval;
- deterministic checks run before any optional model-assisted explanation;
- every action emits a JSONL audit record;
- iteration and time budgets prevent unbounded loops;
- failed verification stops the loop instead of repeatedly retrying risky actions.

## Components

- `policy.json`: allowed actions, budgets, approval requirements, and stop conditions.
- `run_loop.py`: standard-library reference runner.
- `tasks/sample_tasks.jsonl`: deterministic portfolio tasks.
- `.github/workflows/harness-eval.yml`: CI evaluation gate.

## Usage

```bash
python harness/run_loop.py \
  --tasks harness/tasks/sample_tasks.jsonl \
  --policy harness/policy.json \
  --out artifacts/harness-results.jsonl
```

The current runner validates safe repository artifacts. It does not autonomously edit the repository or execute endpoint remediation.

## Extension points

A future planner may be connected through a narrow adapter that returns structured proposals. The policy gate remains deterministic and independent of the model. Harness CI/CD can also invoke the same command as a pipeline step; the repository does not depend on the commercial platform.
