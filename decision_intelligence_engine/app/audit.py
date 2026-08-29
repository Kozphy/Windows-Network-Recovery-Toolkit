from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class HashChainAuditLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return GENESIS
        last = self.path.read_text(encoding="utf-8").splitlines()[-1]
        return json.loads(last)["hash"]

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
            "prev_hash": self._last_hash(),
        }
        digest = hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()
        final = {**record, "hash": digest}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(final) + "\n")
        return final

    def verify(self) -> tuple[bool, int]:
        if not self.path.exists():
            return True, 0
        previous = GENESIS
        count = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            claimed = item.pop("hash")
            if item["prev_hash"] != previous:
                return False, count
            actual = hashlib.sha256(_canonical(item).encode("utf-8")).hexdigest()
            if actual != claimed:
                return False, count
            previous = claimed
            count += 1
        return True, count
