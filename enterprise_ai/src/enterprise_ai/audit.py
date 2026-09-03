import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


class HashChainedAuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        lines = [
            line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        return json.loads(lines[-1])["event_hash"] if lines else "0" * 64

    def append(self, event_type: str, payload: Any) -> str:
        if is_dataclass(payload):
            payload = asdict(payload)
        body = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
            "previous_hash": self._last_hash(),
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        event_hash = sha256(canonical.encode("utf-8")).hexdigest()
        record = {**body, "event_hash": event_hash}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        return event_hash
