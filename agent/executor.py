"""Guarded repair execution for script-based remediation steps.

This module executes planner-produced script steps under strict safety gates.
It is the only local-agent component that mutates host state by launching
repair scripts.

Key invariants:
    - No step runs unless policy checks in `should_run` succeed.
    - Firewall reset requires both step confirmation and firewall opt-in flag.
    - Script paths are constrained to repository root boundary.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import RepairPlan, RepairStep


@dataclass(frozen=True)
class ExecutionResult:
    """Execution result for a single repair step.

    Attributes:
        script: Repository-relative script path.
        returncode: Exit code (-1/-2 are policy/path guard outcomes).
        stdout: Captured stdout/stderr tail or guard message.
    """

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
        """Initialize executor with confirmation policy context.

        Args:
            repo_root: Repository root used for script path resolution.
            confirm_firewall: Explicit opt-in for firewall reset script.
            confirmed_scripts: Set of script paths approved by user/operator.
        """
        self.repo_root = repo_root.resolve()
        self.confirm_firewall = confirm_firewall
        self.confirmed_scripts = frozenset(
            self._normalize_script_path(path) for path in (confirmed_scripts or frozenset())
        )

    @staticmethod
    def _normalize_script_path(rel: str) -> str:
        """Normalize repository-relative script paths for policy comparisons."""
        return rel.replace("/", "\\").lower()

    def _resolve_script(self, rel: str) -> Path:
        """Resolve and validate script path under repository root.

        Args:
            rel: Relative script path from repair plan.

        Returns:
            Path: Resolved absolute script path.

        Raises:
            ValueError: If resolved path escapes repository root.
        """
        candidate = (self.repo_root / rel).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError(f"Script path escapes repo root: {rel}") from exc
        return candidate

    def should_run(self, step: RepairStep) -> tuple[bool, str]:
        """Evaluate whether a step is allowed to execute.

        Args:
            step: Candidate repair step.

        Returns:
            tuple[bool, str]: Allow/deny decision and reason message.
        """
        script_key = self._normalize_script_path(step.script_relative_path)
        if "reset_firewall" in script_key:
            if not self.confirm_firewall:
                return False, "Blocked: firewall reset requires explicit confirmation flag."
        if step.requires_confirmation or step.destructive:
            if script_key not in self.confirmed_scripts:
                return False, "Blocked: step requires explicit confirmation."
        return True, "ok"

    def execute_plan(self, plan: RepairPlan) -> list[ExecutionResult]:
        """Execute all allowed steps in a repair plan.

        Side effects:
            Launches Windows batch scripts via `cmd /c`.

        Idempotency:
            Not guaranteed. Re-running may apply the same repair repeatedly.

        Audit Notes:
            - What can go wrong: policy misconfiguration, missing scripts,
              subprocess timeout, non-zero script exit.
            - Detection: inspect per-step return code and output tail.
            - Recovery: rerun diagnosis, confirm step list, retry targeted step.

        Args:
            plan: Repair plan from planner.

        Returns:
            list[ExecutionResult]: One result entry per plan step.

        Raises:
            subprocess.TimeoutExpired: If launched script exceeds timeout.
            OSError: If subprocess cannot be started.
        """
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
    """Serialize execution results for API/CLI JSON output.

    Args:
        results: Execution result objects.

    Returns:
        list[dict[str, Any]]: JSON-safe result dictionaries.
    """
    return [
        {"script": r.script, "returncode": r.returncode, "stdout_tail": r.stdout}
        for r in results
    ]
