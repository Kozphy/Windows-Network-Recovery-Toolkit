"""Render parent/child process chains for proxy investigation reports."""

from __future__ import annotations

from typing import Any


def build_process_chain_nodes(
    *,
    focus_pid: int | None,
    process_rows: list[dict[str, Any]],
    matched_port: int | None,
) -> list[dict[str, Any]]:
    """Walk parent pointers from focus PID upward; attach listen annotation on focus."""
    if focus_pid is None:
        return []
    by_pid = {int(r["pid"]): r for r in process_rows if isinstance(r.get("pid"), int)}
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    pid: int | None = focus_pid
    while pid is not None and pid not in seen and pid > 4:
        seen.add(pid)
        row = by_pid.get(pid) or {}
        chain.append(
            {
                "pid": pid,
                "process_name": row.get("process_name") or row.get("parent_process_name"),
                "executable_path": row.get("executable_path"),
                "command_line": row.get("command_line"),
                "parent_pid": row.get("parent_pid"),
                "listens_on_localhost_port": matched_port if pid == focus_pid else None,
            }
        )
        ppid = row.get("parent_pid")
        pid = int(ppid) if isinstance(ppid, int) else None
    return list(reversed(chain))


def render_process_tree_text(
    nodes: list[dict[str, Any]],
    *,
    matched_port: int | None = None,
) -> str:
    """Human-readable tree, e.g. Cursor.exe -> powershell.exe -> node.exe (listens on PORT)."""
    if not nodes:
        return "(no process tree resolved)"
    lines: list[str] = []
    depth = 0
    for node in nodes:
        name = str(node.get("process_name") or "unknown")
        prefix = "  " * depth + ("└─ " if depth else "")
        port = node.get("listens_on_localhost_port") or (
            matched_port if depth == len(nodes) - 1 else None
        )
        if port:
            lines.append(f"{prefix}{name}\n{'  ' * (depth + 1)}└─ listens on 127.0.0.1:{port}")
        else:
            lines.append(f"{prefix}{name}")
        depth += 1
    return "\n".join(lines)


def render_process_tree_json(
    nodes: list[dict[str, Any]],
    *,
    matched_port: int | None = None,
) -> dict[str, Any]:
    """Structured nested tree for JSON reports."""
    if not nodes:
        return {"root": None, "matched_localhost_port": matched_port}
    root: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    for node in nodes:
        item = {
            "pid": node.get("pid"),
            "process_name": node.get("process_name"),
            "executable_path": node.get("executable_path"),
            "command_line": node.get("command_line"),
            "listens_on_localhost_port": node.get("listens_on_localhost_port")
            or (matched_port if node is nodes[-1] else None),
            "children": [],
        }
        if root is None:
            root = item
            current = item
        elif current is not None:
            current["children"].append(item)
            current = item
    return {"root": root, "matched_localhost_port": matched_port, "flat_chain": nodes}
