"""Report signing placeholder — hash fingerprint for exports."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sign_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"signature_status": "unsigned", "content_hash_sha256": digest}
