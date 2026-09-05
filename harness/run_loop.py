from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if raw.strip():
            yield line_number, json.loads(raw)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_task(root: Path, task: dict[str, Any]) -> tuple[bool, str]:
    action = task.get("action")
    relative_path = task.get("path")
    if not isinstance(relative_path, str):
        return False, "invalid path"

    target = (root / relative_path).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        return False, "path escapes repository root"

    if action == "check_path_exists":
        return target.exists(), f"exists={target.exists()}"

    if action == "check_text_contains":
        expected = task.get("contains")
        if not isinstance(expected, str) or not target.is_file():
            return False, "missing file or expected text"
        content = target.read_text(encoding="utf-8", errors="replace")
        return expected in content, f"content_sha256={sha256_text(content)}"

    return False, f"unsupported action: {action}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded repository verification harness")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    policy = load_json(args.policy)
    allowed = set(policy.get("allowed_actions", []))
    max_iterations = int(policy.get("budgets", {}).get("max_iterations", 1))
    policy_version = str(policy.get("version", "unknown"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    processed = 0

    with args.out.open("w", encoding="utf-8") as output:
        for line_number, task in iter_jsonl(args.tasks):
            if processed >= max_iterations:
                break
            processed += 1
            started = time.time()
            action = task.get("action")

            if action not in allowed:
                passed, detail, stop_reason = False, "action denied by policy", "policy_denied"
            else:
                passed, detail = verify_task(args.root, task)
                stop_reason = "verification_passed" if passed else "verification_failed"

            failures += int(not passed)
            record = {
                "task_id": task.get("id", f"line-{line_number}"),
                "action": action,
                "passed": passed,
                "detail": detail,
                "stop_reason": stop_reason,
                "policy_version": policy_version,
                "duration_ms": round((time.time() - started) * 1000, 3),
            }
            output.write(json.dumps(record, sort_keys=True) + "\n")

    print(json.dumps({"processed": processed, "failures": failures, "output": str(args.out)}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
