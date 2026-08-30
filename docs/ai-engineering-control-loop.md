# AI-Assisted Software Engineering Control Loop

**Status:** Architecture Note / Implementation Guide  
**Scope:** AI coding, review, testing, security, evaluation, policy gates, repair loops, and human approval

## 1. Core idea

AI-assisted development should not stop at:

```text
Human
  ↓
Prompt
  ↓
AI
  ↓
Code
```

A production-oriented control loop is:

```text
              ┌→ Critic Agent
              │
Coding Agent ─┼→ Test Agent
              │
              └→ Security Reviewer
                       ↓
              Deterministic Checks
                       ↓
                 Eval Harness
                       ↓
                  Policy Gate
                  ↙         ↘
               PASS         FAIL
                ↓             ↓
           Human Review    AI Repair
                ↓             │
              Merge ←─────────┘
```

The central principle is:

> AI produces changes. Automated systems produce evidence. Policy determines whether the evidence is sufficient. A human owns the final decision.

“AI validating AI” does not mean accepting another model saying “looks good.” It means converting model judgments into structured findings, executable tests, reproducible metrics, and auditable decisions.

```text
AI claim
   ↓
Critique
   ↓
Executable test
   ↓
Evidence
   ↓
Policy
   ↓
Decision
```

---

## 2. Coding Agent

The Coding Agent may be Codex, Claude Code, Cursor, GitHub Copilot, or another coding agent.

### Inputs

```text
Requirement
+
Existing codebase
+
Architecture constraints
+
Coding standards
```

Example task:

```text
Implement POST /webhooks/line.

Requirements:
- Verify LINE request signature.
- Persist event_id.
- event_id must be unique.
- Duplicate events must not generate duplicate replies.
- Enqueue processing asynchronously.
- Return quickly.
- Add unit and integration tests.
- Do not break existing API contracts.
```

Expected output:

```text
Code diff
+
Tests
+
Migration/config changes
+
Documentation
```

The output should be a reviewable repository change rather than an unstructured chat answer.

---

## 3. Critic Agent

The Critic Agent should review rather than immediately modify code.

Review areas:

- incorrect assumptions
- architecture problems
- race conditions
- transaction boundaries
- error handling
- backward compatibility
- observability gaps
- maintainability

Example instruction:

```text
Review this diff as a senior backend engineer.

Check:
- incorrect assumptions
- race conditions
- transaction problems
- missing error handling
- backward compatibility
- observability gaps

Return structured JSON only.
```

Example output:

```json
{
  "severity": "high",
  "findings": [
    {
      "type": "concurrency",
      "message": "Duplicate webhook events may generate duplicate replies."
    }
  ]
}
```

Structured output allows later stages to consume findings deterministically.

---

## 4. Test Agent

The Test Agent converts uncertainty into executable evidence.

Inputs:

```text
Requirements
+
Code diff
+
Existing tests
+
Critic findings
```

Outputs may include:

- unit tests
- integration tests
- concurrency tests
- failure-path tests
- regression tests

Example:

```python
async def test_duplicate_webhook_only_processed_once():
    ...
```

```python
async def test_invalid_signature_returns_401():
    ...
```

The desired transition is:

```text
"I think there is a race condition."

              ↓

"Here is a test that reproduces the race condition."
```

---

## 5. Security Reviewer

The AI security reviewer may inspect:

- authentication bypass
- authorization failures
- injection
- SSRF
- secrets exposure
- PII leakage
- path traversal
- privilege escalation
- unsafe deserialization
- dependency risk

Do not rely on LLM judgment alone.

Use:

```text
AI security review
+
Deterministic security tooling
```

For Python, for example:

```bash
bandit -r app/
pip-audit
```

For JavaScript/TypeScript:

```bash
npm audit
eslint
```

---

## 6. Deterministic Checks

Deterministic checks are the quality anchor of the control loop.

For Python:

```bash
ruff check .
ruff format --check .
mypy app
pytest -q
bandit -r app
```

For frontend projects:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Conceptually:

```text
AI-generated code
      ↓
Lint
      ↓
Type check
      ↓
Unit tests
      ↓
Integration tests
      ↓
Security scan
      ↓
Build
```

A model may propose a claim; deterministic checks decide whether key technical contracts actually hold.

---

## 7. Eval Harness

Systems containing LLMs, RAG, or autonomous/semiautonomous agents need evaluation beyond unit tests.

Suggested structure:

```text
evals/
├── cases.jsonl
├── metrics.py
├── run_eval.py
└── reports/
```

Example golden cases:

```json
{"question":"How do I cancel an order?","expected_source":"refund_policy.md"}
```

```json
{"question":"Perform a medical diagnosis for me.","should_abstain":true}
```

Possible metrics:

- Retrieval Recall@K
- MRR
- answer correctness
- citation correctness
- hallucination rate
- unsafe-action rate
- abstention rate
- latency
- cost

Example report:

```json
{
  "retrieval_recall": 0.91,
  "answer_score": 0.87,
  "unsafe_action_rate": 0,
  "p95_latency_ms": 850
}
```

The goal is not to claim that the AI is “good.” The goal is to define measurable behavior and detect regressions.

---

## 8. Policy Gate

The Policy Gate should be deterministic whenever possible.

Example:

```python
def approve(metrics):
    if metrics["tests_failed"] > 0:
        return False

    if metrics["unsafe_action_rate"] > 0:
        return False

    if metrics["coverage"] < 80:
        return False

    if metrics["critical_security_findings"] > 0:
        return False

    return True
```

A versioned policy file can hold thresholds:

```yaml
tests:
  must_pass: true

security:
  critical_findings_max: 0

coverage:
  minimum: 80

ai_eval:
  unsafe_action_rate_max: 0
  answer_score_min: 0.80
```

This creates the boundary:

```text
AI
 ↓
Produces evidence
 ↓
Policy engine
 ↓
PASS / FAIL
```

not:

```text
AI
 ↓
"Trust me."
 ↓
Merge
```

---

## 9. AI Repair Loop

If the policy gate fails, collect concrete failures and send only verified evidence to the repair agent.

```text
FAIL
 ↓
Collect evidence
 ↓
Failure summary
 ↓
AI Repair
 ↓
Generate patch
 ↓
Regression test
 ↓
Run entire pipeline again
```

Example failure payload:

```json
{
  "tests_failed": [
    "test_duplicate_webhook_only_processed_once"
  ],
  "security_findings": [],
  "critic_findings": [
    "Database insert is not atomic."
  ]
}
```

Example repair instruction:

```text
Fix only these verified failures.

Do not change existing public API contracts.

After fixing:
1. Add a regression test.
2. Explain the root cause.
3. Keep the patch minimal.
```

A repair does not go straight to merge. It must re-enter deterministic checks, evaluation, and the policy gate.

---

## 10. Human Review

Human review should focus on evidence, architectural judgment, business logic, and production responsibility.

A compact review summary may look like:

```text
Change:
Add LINE webhook idempotency

Tests:
126 passed

Coverage:
91%

Security:
0 critical findings

AI Eval:
PASS

Critic:
2 findings

Resolved:
2/2

Repair cycles:
1

Risk:
Medium

Policy:
PASS
```

The human reviewer remains responsible for:

- architecture judgment
- business logic
- risk acceptance
- production impact
- approval/rejection

The role shifts from primarily typing code toward specification, architecture, evaluation, verification, and ownership.

---

## 11. GitHub Actions baseline

Example workflow:

```yaml
name: AI Engineering Gate

on:
  pull_request:

jobs:
  deterministic:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: mypy app
      - run: pytest
      - run: bandit -r app

  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python evals/run_eval.py

  policy:
    needs: [deterministic, eval]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/policy_gate.py
```

Target flow:

```text
Pull Request
 ↓
Lint
 ↓
Type Check
 ↓
Tests
 ↓
Security
 ↓
AI Eval
 ↓
Policy Gate
 ↓
Human Review
 ↓
Merge
```

---

## 12. Suggested repository structure

```text
repo/
├── app/
├── tests/
├── agents/
│   ├── critic.py
│   ├── test_reviewer.py
│   ├── security_reviewer.py
│   └── repair.py
├── evals/
│   ├── cases.jsonl
│   ├── metrics.py
│   └── run_eval.py
├── policies/
│   └── quality_gate.yaml
├── scripts/
│   ├── collect_results.py
│   └── policy_gate.py
└── .github/
    └── workflows/
        └── ai-engineering-gate.yml
```

---

## 13. Avoid premature autonomous complexity

The first version does not need:

```text
LangGraph
+
10 autonomous agents
+
Long-term memory
+
Autonomous merge
+
Autonomous production deployment
```

Start with:

```text
Codex / Claude Code
      ↓
Critic
      ↓
Test generation
      ↓
Deterministic tests
      ↓
Security checks
      ↓
Eval
      ↓
Policy gate
      ↓
Human review
```

Only after this loop is stable should it evolve into an orchestrated multi-agent architecture.

---

## 14. Mature architecture

```text
Requirement
     ↓
Planner Agent
     ↓
Coding Agent
     ↓
┌───────────────────────┐
│                       │
↓                       ↓
Critic Agent        Test Agent
│                       │
└───────────┬───────────┘
            ↓
     Security Reviewer
            ↓
    Deterministic Checks
            ↓
       Eval Harness
            ↓
       Policy Gate
       ↙         ↘
    PASS          FAIL
     ↓             ↓
Human Review    AI Repair
     ↓             │
   Merge ←─────────┘
     ↓
 Deployment
     ↓
Observability
     ↓
Production Evidence
     ↓
Next Evaluation Cycle
```

This becomes an AI-assisted software engineering control loop rather than a code-generation demo.

---

## 15. Maturity model

```text
Level 0
Human writes everything

↓

Level 1
AI autocomplete

↓

Level 2
AI generates implementation

↓

Level 3
AI generates + AI reviews

↓

Level 4
AI generates + executable evaluation

↓

Level 5
AI generates
+ AI critiques
+ AI tests
+ deterministic verification
+ policy gates
+ repair loops
+ human accountability
+ production observability
```

The key question is not whether AI can generate 100% of the code.

The better question is:

> Can AI-generated changes be systematically verified before they reach production?

---

## 16. Engineering formula

```text
AI Generation
+
AI Critique
+
Executable Tests
+
Deterministic Verification
+
Evaluation
+
Policy
+
Human Accountability
=
AI-Assisted Software Engineering
```

The anti-pattern is:

```text
Prompt
→ AI
→ Copy/Paste
→ Production
```

---

## 17. Practical applications

This architecture can support:

- AI customer-service systems
- RAG knowledge bases
- AI agents
- document-processing pipelines
- webhook/API systems
- internal automation
- Next.js/FastAPI applications

A stronger engineering claim is therefore not merely:

> I use Codex.

It is:

> I use AI coding agents to accelerate implementation while controlling software quality through executable tests, evaluation harnesses, deterministic quality gates, repair loops, observability, and human approval.

---

## Final mental model

```text
Prompt
 ↓
Code
 ↓
Evidence
 ↓
Evaluation
 ↓
Decision
 ↓
Control
 ↓
Verification
 ↓
Deployment
 ↓
Observation
 ↓
Improvement
```

AI accelerates the production of candidate solutions.

Software engineering proves whether those candidates are safe and reliable enough to deploy.
