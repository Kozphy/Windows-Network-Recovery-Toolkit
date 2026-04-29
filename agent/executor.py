"""Execute approved repair scripts only; never auto-run destructive or firewall resets."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import RepairPlan, RepairStep


@dataclass(frozen=True)
class ExecutionResult:
    script: str
    returncode: int
    stdout: str


class RepairExecutor:
    """
    Runs `.bat` files relative to repository root.

    Policy:
    - Steps with `requires_confirmation` execute only if `confirmed` includes their script path.
    - `reset_firewall.bat` additionally requires `confirm_firewall=True`.
    - Nothing runs automatically unless explicitly allowed per-step below.
    """

    def __init__(
        self,
        repo_root: Path,
        *,
        confirm_firewall: bool = False,
        confirmed_scripts: frozenset[str] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.confirm_firewall = confirm_firewall
        self.confirmed_scripts = confirmed_scripts or frozenset()

    def _resolve_script(self, rel: str) -> Path:
        candidate = (self.repo_root / rel).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"Script path escapes repo root: {rel}") from exc
        return candidate

    def should_run(self, step: RepairStep) -> tuple[bool, str]:
        name_lower = step.script_relative_path.replace("/", "\\").lower()
        if "reset_firewall" in name_lower:
            if not self.confirm_firewall:
                return False, "Blocked: firewall reset requires explicit confirmation flag."
        if step.requires_confirmation or step.destructive:
            if step.script_relative_path not in self.confirmed_scripts:
                return False, "Blocked: step requires explicit confirmation."
        return True, "ok"

    def execute_plan(self, plan: RepairPlan) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        for step in plan.steps:
            ok, reason = self.should_run(step)
            if not ok:
                results.append(
                    ExecutionResult(
                        script=step.script_relative_path,
                        returncode=-1,
                        stdout=reason,
                    ),
                )
                continue
            target = self._resolve_script(step.script_relative_path)
            if not target.is_file():
                results.append(
                    ExecutionResult(
                        script=step.script_relative_path,
                        returncode=-2,
                        stdout=f"Missing script file: {target}",
                    ),
                )
                continue
            proc = subprocess.run(
                ["cmd", "/c", str(target)],
                capture_output=True,
                text=True,
                cwd=str(self.repo_root),
                timeout=600,
                shell=False,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            results.append(
                ExecutionResult(
                    script=step.script_relative_path,
                    returncode=proc.returncode,
                    stdout=out[-8000:],
                ),
            )
        return results


def results_to_payload(results: list[ExecutionResult]) -> list[dict[str, Any]]:
    return [
        {"script": r.script, "returncode": r.returncode, "stdout_tail": r.stdout}
        for r in results
    ]
