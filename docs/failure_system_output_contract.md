# Failure System output contract

Defines the stdout contract for:

```powershell
python -m failure_system diagnose
```

This document covers **presentation and schema behavior only**. It does **not** change diagnostic
rules, confidence scoring, storage paths, or repair safety boundaries.

---

## Goals

- Keep default CLI output easy to scan for operators.
- Keep machine-evidence JSON complete for automation.
- Keep markdown output reusable for incident notes and portfolio/demo docs.
- Keep verbose output suitable for troubleshooting without changing evidence semantics.

Core principle:

- **JSON = evidence layer**
- **Human summary = decision layer**
- **Markdown = communication layer**
- **Verbose = debugging layer**
- **JSONL = audit layer**

---

## Command modes

`diagnose` supports mutually exclusive output flags:

- `--json`
- `--markdown`
- `--verbose`

If none are provided, default is **human summary**.

`--diagram` remains supported and cannot be combined with the output flags above.

---

## 1) Default mode (`diagnose`)

### Contract

Print a concise decision-focused summary to stdout.

### Must include

- `Diagnosis Summary`
- `Observed Signals`
- `Rule Outcome`
- `Recommended Action`
- `Safety Boundary`

### Must not include by default

- raw `diagnostic_commands` body dumps (e.g., `ipconfig_all`, `route_print`, HTML from curl probes)

### Intended users

- operators running interactive diagnosis
- demos where quick readability matters

---

## 2) JSON mode (`diagnose --json`)

### Contract

Print full machine-readable result JSON only:

```python
json.dumps(result, indent=2, ensure_ascii=False)
```

### Field preservation requirement

Do not remove these fields when present:

- `failure_block.diagnostic_commands`
- `failure_block.source_logs`
- `failure_block.safety_boundary`
- `failure_block.rollback_plan`
- `rule_outcomes`
- `stored_path`
- `explanation_text`

### Intended users

- scripts
- CI checks
- downstream APIs/dashboards

---

## 3) Markdown mode (`diagnose --markdown`)

### Contract

Print a Markdown report suitable for:

- GitHub issues
- incident notes
- runbooks
- architecture/demo docs

### Required sections

- `## Diagnosis Result`
- `### Observed Signals`
- `### Rule Outcomes`
- `### Recommended Action`
- `### Safety Boundary`

Markdown tables should be used for summary fields and signal/rule rows.

---

## 4) Verbose mode (`diagnose --verbose`)

### Contract

Print default human summary first, then append a raw evidence section.

### Required additions

- `Raw Evidence` section
- named command sections like `[ping_8_8_8_8]`
- source logs when present
- explanation text
- rollback plan

### Intended users

- debugging probe quality
- investigating rule mismatches
- post-incident local evidence review

---

## Stability and compatibility

### Stable behavior (expected)

- Mode selection semantics and mutual exclusivity.
- Presence of top-level keys in `--json` output (`failure_block`, `rule_outcomes`, `stored_path`, `explanation_text`).
- Safety text remains visible in human-facing modes.

### May evolve

- exact wording and spacing in human/markdown output
- additional optional fields in JSON payloads
- ordering of non-semantic presentation blocks

### Versioning guidance

If a future change removes or renames JSON keys, add a `schema_version` field and document migration.

---

## Audit and troubleshooting notes

- Canonical persisted evidence remains JSONL shards under `data/failure_blocks/`.
- `stored_path` in diagnose output should point to the appended shard for the current run.
- If terminal output is ambiguous, rely on:
  - `diagnose --json`
  - persisted JSONL rows
  - `search` / `recommend` commands

This output contract does not authorize any automatic repair behavior; `failure_system` remains
diagnostics-first and read-only in execution scope.

