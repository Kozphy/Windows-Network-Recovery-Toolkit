"""Investigation vocabulary and audit paths."""

from __future__ import annotations

SCHEMA_VERSION = "proxy_investigation.v1"
ENGINE_VERSION = "2026.05"
AUDIT_JSONL = "logs/proxy_investigation.jsonl"
REPORT_DIR_NAME = "reports/proxy_investigations"

ATTRIBUTION_LISTENER_ONLY = (
    "Listener/process correlation does not prove which process modified WinINET registry values."
)
MALWARE_FORBIDDEN = "Do not label activity as malware or confirmed attack without proof-tier evidence."

DEV_PROCESS_NAMES = frozenset(
    {
        "node.exe",
        "npm.cmd",
        "npm.exe",
        "electron.exe",
        "code.exe",
        "cursor.exe",
        "devenv.exe",
        "python.exe",
        "pnpm.exe",
        "yarn.exe",
    },
)
