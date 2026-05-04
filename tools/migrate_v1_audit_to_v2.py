#!/usr/bin/env python3
"""Read legacy JSONL audits and emit schema 2.0 rows **without modifying originals**.

Reads::

    logs/repair_audit.jsonl

Writes append-only clones under::

    logs/v2_migrated/*.jsonl

Example::

    python tools/migrate_v1_audit_to_v2.py --repo .

"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.network_state import event_log as v2  # noqa: E402

_V2_SCHEMA = "2.0"


def migrate_row(row: dict[str, Any], *, source_line: str) -> list[dict[str, Any]]:
    """Emit v2 dict rows from one v1-ish ``repair_audit`` line (best-effort)."""

    out: list[dict[str, Any]] = []
    ts = row.get("timestamp") or v2.utc_now()

    observed: dict[str, Any] | None = None
    before = row.get("before")
    if isinstance(before, dict):
        values = before.get("values") if isinstance(before.get("values"), dict) else before
        if isinstance(values, dict):
            if any(k in values for k in ("ProxyEnable", "proxy_enable", "ProxyServer", "proxy_server")):
                observed = {
                    "ProxyEnable": values.get("ProxyEnable", values.get("proxy_enable")),
                    "ProxyServer": values.get("ProxyServer", values.get("proxy_server")),
                    "AutoConfigURL": values.get("AutoConfigURL", values.get("auto_config_url")),
                    "AutoDetect": values.get("AutoDetect", values.get("auto_detect")),
                    "ProxyOverride": values.get("ProxyOverride", values.get("proxy_override")),
                }

    after = row.get("after")
    if observed is None and isinstance(after, dict):
        observed = {
            "ProxyEnable": after.get("proxy_enable"),
            "ProxyServer": after.get("proxy_server"),
            "AutoConfigURL": after.get("auto_config_url"),
            "AutoDetect": after.get("auto_detect"),
            "ProxyOverride": after.get("proxy_override"),
        }

    proxy_server_guess = ""
    if isinstance(observed, dict):
        ps = observed.get("ProxyServer") or ""
        proxy_server_guess = ps.strip() if isinstance(ps, str) else str(ps)
    corr = v2.correlation_key(proxy_server_guess if proxy_server_guess else None)
    inc = v2.incident_id_from_proxy(proxy_server_guess if proxy_server_guess else None)

    snap_eid = v2.new_event_id()
    repair_ids: list[str] = []

    if observed is not None:
        snapshot_row = {
            "schema_version": _V2_SCHEMA,
            "event_type": "snapshot",
            "event_id": snap_eid,
            "timestamp_utc": str(ts),
            "incident_id": inc,
            "correlation_key": corr,
            "scope": "HKCU",
            "source": "wininet_registry",
            "observed": observed,
            "parsed": dict(v2.parse_proxy(observed)),
            "_migrated_from": "repair_audit.jsonl",
        }
        out.append(snapshot_row)

    results = row.get("results") if isinstance(row.get("results"), list) else []
    planned = row.get("planned_action") if isinstance(row.get("planned_action"), dict) else {}

    if isinstance(results, list) and results:
        for r in results:
            if not isinstance(r, dict):
                continue
            argv = r.get("argv")
            if not isinstance(argv, list):
                continue
            rid = v2.new_event_id()
            repair_ids.append(rid)
            action_type = "disable_wininet_hkcu_proxy"
            if argv[:2] == ["reg", "delete"]:
                action_type = "delete_wininet_proxyserver_value"
            out.append(
                {
                    "schema_version": _V2_SCHEMA,
                    "event_type": "repair_attempt",
                    "event_id": rid,
                    "timestamp_utc": str(ts),
                    "incident_id": inc,
                    "correlation_key": corr,
                    "snapshot_event_id": snap_eid if observed is not None else rid,
                    "action_type": action_type,
                    "target": {},
                    "mutation_argv": [str(x) for x in argv],
                    "result": {
                        "exit_code": int(r.get("code", -1)),
                        "stdout": str(r.get("stdout") or "")[:4000],
                        "stderr": str(r.get("stderr") or "")[:4000],
                        "command_success": int(r.get("code", -1)) == 0,
                    },
                    "confirmation": {
                        "required": True,
                        "method": str(row.get("confirmation_method") or "typed_phrase"),
                    },
                    "risk": {
                        "risk_level": "low",
                        "changes_winhttp": False,
                        "changes_system_proxy": False,
                        "changes_hkcu_only": True,
                    },
                    "_migrated_from": "repair_audit.jsonl",
                }
            )

    elif isinstance(planned, dict) and planned.get("mutation_argv"):
        for argv in planned.get("mutation_argv") or []:
            if not isinstance(argv, list):
                continue
            rid = v2.new_event_id()
            repair_ids.append(rid)
            out.append(
                {
                    "schema_version": _V2_SCHEMA,
                    "event_type": "repair_attempt",
                    "event_id": rid,
                    "timestamp_utc": str(ts),
                    "incident_id": inc,
                    "correlation_key": corr,
                    "snapshot_event_id": snap_eid if observed is not None else rid,
                    "action_type": "disable_wininet_hkcu_proxy",
                    "target": {},
                    "mutation_argv": [str(x) for x in argv],
                    "result": {
                        "exit_code": 0,
                        "stdout": "",
                        "stderr": "",
                        "command_success": True,
                    },
                    "confirmation": {"required": True, "method": "typed_phrase"},
                    "risk": {
                        "risk_level": "low",
                        "changes_winhttp": False,
                        "changes_system_proxy": False,
                        "changes_hkcu_only": True,
                    },
                    "_migrated_from": "repair_audit.jsonl",
                    "_migrated_note": "planned_action only (no stdout/stderr on v1 row)",
                }
            )

    ver = row.get("verification_result")
    if isinstance(ver, dict):
        link = repair_ids[0] if repair_ids else f"migrated:no_repair:{snap_eid}"
        obs_ver: dict[str, Any] = {}
        if isinstance(after, dict):
            obs_ver = {
                "ProxyEnable": after.get("proxy_enable"),
                "ProxyServer": after.get("proxy_server"),
            }
        out.append(
            {
                "schema_version": _V2_SCHEMA,
                "event_type": "verification",
                "event_id": v2.new_event_id(),
                "timestamp_utc": str(ts),
                "incident_id": inc,
                "correlation_key": corr,
                "repair_event_id": link,
                "expected": {"ProxyEnable": ver.get("expected_proxy_enable", 0)},
                "observed": obs_ver,
                "ok": bool(ver.get("ok")),
                "confidence": 0.99 if ver.get("ok") else 0.4,
                "interpretation": str(ver.get("detail") or ""),
                "_migrated_from": "repair_audit.jsonl",
            }
        )

    if not out:
        out.append(
            {
                "schema_version": _V2_SCHEMA,
                "event_type": "migration_skip",
                "event_id": v2.new_event_id(),
                "timestamp_utc": v2.utc_now(),
                "incident_id": inc,
                "correlation_key": corr,
                "reason": "unrecognized_v1_row_shape",
                "source_line_sha256": hashlib.sha256(source_line.encode("utf-8")).hexdigest(),
            }
        )

    return out


def _route_row(event_type: str, row: dict[str, Any], dest: dict[str, Path]) -> None:
    if event_type == "snapshot":
        p = dest["snapshots"]
    elif event_type == "repair_attempt":
        p = dest["repairs"]
    elif event_type == "verification":
        p = dest["verifications"]
    elif event_type == "drift_detected":
        p = dest["drifts"]
    elif event_type == "attribution":
        p = dest["attribution"]
    elif event_type == "incident_summary":
        p = dest["incidents"]
    else:
        p = dest["other"]
    line = json.dumps(row, ensure_ascii=False)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate v1 repair_audit.jsonl hints to v2 JSONL clones.")
    ap.add_argument("--repo", type=Path, default=None, help="Toolkit root (defaults to checkout containing tools/).")
    args = ap.parse_args()
    repo = (args.repo or _ROOT).resolve()
    src = repo / "logs" / "repair_audit.jsonl"
    out_dir = repo / "logs" / "v2_migrated"
    dest = {
        "snapshots": out_dir / "snapshots.jsonl",
        "repairs": out_dir / "repairs.jsonl",
        "verifications": out_dir / "verifications.jsonl",
        "drifts": out_dir / "drifts.jsonl",
        "attribution": out_dir / "attribution.jsonl",
        "incidents": out_dir / "incidents.jsonl",
        "other": out_dir / "unclassified.jsonl",
    }
    if not src.is_file():
        print(f"No source file: {src}", file=sys.stderr)
        return 1

    for p in dest.values():
        if p.is_file():
            p.unlink()

    with src.open(encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                row_obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row_obj, dict):
                continue
            if row_obj.get("type") != "repair" or row_obj.get("subtype") != "proxy_disable":
                continue
            for v2_row in migrate_row(row_obj, source_line=raw):
                _route_row(str(v2_row.get("event_type")), v2_row, dest)

    print(f"Wrote v2 clones under {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
