"""Typed models for process classification (Step 2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProcessClassificationKind(str, Enum):
    KNOWN_CURSOR_PROXY = "KNOWN_CURSOR_PROXY"
    KNOWN_VSCODE_EXTENSION = "KNOWN_VSCODE_EXTENSION"
    KNOWN_DEV_PROXY = "KNOWN_DEV_PROXY"
    KNOWN_SECURITY_TOOL = "KNOWN_SECURITY_TOOL"
    KNOWN_BROWSER_PROXY = "KNOWN_BROWSER_PROXY"
    UNKNOWN_LOCAL_PROXY = "UNKNOWN_LOCAL_PROXY"
    SUSPICIOUS_PROXY = "SUSPICIOUS_PROXY"
    POSSIBLE_MITM_RISK = "POSSIBLE_MITM_RISK"
    REGISTRY_WRITER_CONFIRMED = "REGISTRY_WRITER_CONFIRMED"
    BENIGN_SYSTEM_CHANGE = "BENIGN_SYSTEM_CHANGE"
    CORRELATION_ONLY = "CORRELATION_ONLY"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProcessNode:
    process_guid: str | None = None
    image_path: str | None = None
    process_name: str | None = None
    process_id: int | None = None
    command_line: str | None = None
    parent_process_guid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_guid": self.process_guid,
            "image_path": self.image_path,
            "process_name": self.process_name,
            "process_id": self.process_id,
            "command_line": self.command_line,
            "parent_process_guid": self.parent_process_guid,
        }


@dataclass
class ProcessClassificationInput:
    image_path: str | None = None
    process_name: str | None = None
    process_guid: str | None = None
    process_id: int | None = None
    command_line: str | None = None
    parent_image_path: str | None = None
    parent_process_name: str | None = None
    parent_command_line: str | None = None
    ancestor_chain: list[ProcessNode] = field(default_factory=list)
    hashes: dict[str, str] | None = None
    signature_status: str | None = None
    user: str | None = None
    working_directory: str | None = None
    registry_target: str = ""
    registry_value_name: str = ""
    registry_details: str | None = None
    proxy_server_after: str | None = None
    localhost_port: int | None = None
    event_timestamp_utc: str = ""
    causation_level: str | None = None
    has_registry_writer_proof: bool = False
    has_listener_only: bool = False

    @classmethod
    def from_causation_dict(
        cls,
        causation: dict[str, Any],
        *,
        proxy_server: str | None = None,
        registry_value_name: str = "",
    ) -> ProcessClassificationInput:
        chain = [
            ProcessNode(
                process_guid=n.get("process_guid"),
                image_path=n.get("image"),
                process_name=(n.get("image") or "").split("\\")[-1] if n.get("image") else None,
                command_line=n.get("command_line"),
            )
            for n in (causation.get("process_tree") or [])
            if isinstance(n, dict)
        ]
        image = causation.get("writer_process")
        level = str(causation.get("causation_level") or "")
        return cls(
            image_path=image,
            process_name=(image or "").split("\\")[-1] if image else None,
            process_guid=causation.get("writer_process_guid"),
            process_id=causation.get("writer_pid"),
            command_line=causation.get("writer_command_line"),
            parent_image_path=causation.get("parent_process"),
            parent_process_name=(causation.get("parent_process") or "").split("\\")[-1]
            if causation.get("parent_process")
            else None,
            parent_command_line=causation.get("parent_command_line"),
            ancestor_chain=chain,
            hashes={"raw": causation.get("writer_hashes")} if causation.get("writer_hashes") else None,
            registry_target=str(causation.get("matched_registry_target") or ""),
            registry_value_name=registry_value_name,
            registry_details=causation.get("matched_registry_details"),
            proxy_server_after=proxy_server,
            localhost_port=causation.get("observed_localhost_port"),
            causation_level=level,
            has_registry_writer_proof=level in ("FINAL_CAUSATION", "STRONG_CAUSATION"),
            has_listener_only=level in ("CORRELATION_ONLY", "UNKNOWN"),
        )


@dataclass
class ProcessClassificationResult:
    classification: ProcessClassificationKind
    confidence: float
    reasons: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    trust_factors: list[str] = field(default_factory=list)
    recommended_review: bool = False
    summary: str = ""

    @property
    def label(self) -> str:
        return self.classification.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "label": self.classification.value,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "risk_factors": list(self.risk_factors),
            "trust_factors": list(self.trust_factors),
            "recommended_review": self.recommended_review,
            "summary": self.summary,
            "explanation": self.summary,
        }
