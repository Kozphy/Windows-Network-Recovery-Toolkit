"""Build process lineage from Sysmon Event ID 1 rows (ProcessGuid graph)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.telemetry.sysmon_reader import SysmonEvent


@dataclass
class ProcessTreeNode:
    process_guid: str | None
    process_id: int | None
    image: str | None
    command_line: str | None
    parent_process_guid: str | None = None
    children: list[ProcessTreeNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "process_guid": self.process_guid,
            "process_id": self.process_id,
            "image": self.image,
            "command_line": self.command_line,
            "parent_process_guid": self.parent_process_guid,
            "children": [c.to_dict() for c in self.children],
        }


class ProcessTreeBuilder:
    """Index Sysmon process-create events and walk ancestors by ProcessGuid."""

    def __init__(self, events: list[SysmonEvent]) -> None:
        self._by_guid: dict[str, SysmonEvent] = {}
        for ev in events:
            if ev.event_id != 1 or not ev.process_guid:
                continue
            self._by_guid[ev.process_guid.lower()] = ev

    def get_creation(self, process_guid: str | None) -> SysmonEvent | None:
        if not process_guid:
            return None
        return self._by_guid.get(process_guid.lower())

    def ancestor_chain(self, process_guid: str | None, *, max_depth: int = 6) -> list[dict]:
        """Return ordered list root -> ... -> focus process (max *max_depth* nodes)."""
        chain: list[dict] = []
        guid = process_guid
        seen: set[str] = set()
        depth = 0
        while guid and guid.lower() not in seen and depth < max_depth:
            seen.add(guid.lower())
            ev = self.get_creation(guid)
            if ev is None:
                chain.append(
                    {
                        "process_guid": guid,
                        "process_id": None,
                        "image": None,
                        "command_line": None,
                        "parent_process_guid": None,
                        "note": "process_create_event_missing",
                    }
                )
                break
            chain.append(
                {
                    "process_guid": ev.process_guid,
                    "process_id": ev.process_id,
                    "image": ev.image,
                    "command_line": ev.command_line,
                    "parent_process_guid": ev.parent_process_guid,
                    "parent_image": ev.parent_image,
                    "parent_command_line": ev.parent_command_line,
                }
            )
            guid = ev.parent_process_guid
            depth += 1
        return list(reversed(chain))

    def lineage_for_guid(self, process_guid: str | None, *, max_depth: int = 6) -> ProcessTreeNode | None:
        chain = self.ancestor_chain(process_guid, max_depth=max_depth)
        if not chain:
            return None
        root: ProcessTreeNode | None = None
        current: ProcessTreeNode | None = None
        for row in chain:
            node = ProcessTreeNode(
                process_guid=row.get("process_guid"),
                process_id=row.get("process_id"),
                image=row.get("image"),
                command_line=row.get("command_line"),
                parent_process_guid=row.get("parent_process_guid"),
            )
            if root is None:
                root = node
                current = node
            elif current is not None:
                current.children.append(node)
                current = node
        return root
