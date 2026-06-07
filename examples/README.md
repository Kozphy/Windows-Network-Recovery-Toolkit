# Examples

This folder holds **safe, fictional** samples for documentation and portfolio review.

- **`sample_failure_block.json`** — Synthetic FailureBlock-shaped record with no real hostnames, IPs, or corporate domains.
- **`proxy_reasoning_audit_record.json`** — Fictional `proxy_reasoning_run` row illustrating signals, policy, and limitations.
- **`proof_engine_localhost_proxy_confirmed_example.json`** — Fictional proof contrast example (demo port `127.0.0.1:54321`).
- **`synthetic_platform_audit.jsonl`** — Fictional append-only audit tail (`demo-user`, `demo-ev-001`).

Do **not** add real `logs/`, `reports/`, or JSONL exports from production machines. Use `tests/fixtures/` for automated test inputs.

Copy `config/last_known_good_proxy.example.json` to `config/last_known_good_proxy.json` locally if you need a known-good template (the latter is gitignored).
