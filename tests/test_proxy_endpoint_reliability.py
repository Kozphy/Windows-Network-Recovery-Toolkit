"""Endpoint reliability primitives: parsers, attribution, snapshots, rollback plan, verification.

Tests avoid HKCU mutations; subprocess/registry probes are mocked.
"""

from __future__ import annotations

import io
import json
from argparse import Namespace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.proxy_guard.failure_block import build_proxy_failure_blocks
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.registry import ProxyRegistrySnapshot
from src.proxy_guard.remediation import ProxyDisableMutation
from src.proxy_guard.repair_snapshots import (
    WinInetCapturedState,
    append_proxy_snapshots_jsonl,
    build_restore_reg_argv,
    build_rollback_plan,
    load_snapshot_record_by_id,
    merge_snapshot_payload,
)
from src.proxy_guard.verification import verify_proxy_disabled


def test_parse_proxy_server_ipv6_localhost_bracket() -> None:
    p = parse_proxy_server("[::1]:7890")
    assert p.is_localhost_proxy
    assert p.localhost_port == 7890


def test_parse_multi_scheme_detects_ipv6_localhost() -> None:
    p = parse_proxy_server("http=[::1]:8080")
    assert p.http_localhost_port == 8080
    assert p.is_localhost_proxy


def test_localhost_proxy_detection_plain() -> None:
    assert parse_proxy_server("127.0.0.1:8443").proxy_mode == "manual_localhost"
    assert parse_proxy_server("localhost:1").is_localhost_proxy


def test_no_listener_attribution_payload() -> None:
    fake_netstat = " TCP    127.0.0.1:59999    0.0.0.0:0    LISTENING    777\n"

    def fake_run(cmd: object, **_kwargs: object) -> Any:
        argv = tuple(cmd) if isinstance(cmd, (list, tuple)) else ()
        joined = " ".join(str(x) for x in argv).lower()
        if "powershell" in joined:
            return AnyReturn(0, "{}", "")
        if "netstat" in joined:
            return AnyReturn(0, fake_netstat, "")
        if joined.startswith("tasklist"):
            return AnyReturn(0, '"node.exe","999"\r\n', "")
        return AnyReturn(1, "", "")

    from src.proxy_guard.localhost_attribution import build_localhost_proxy_attribution

    reg = ProxyRegistrySnapshot(1, "127.0.0.1:7890", None, None, None)
    parsed = parse_proxy_server(reg.proxy_server)
    attrib = build_localhost_proxy_attribution(reg, parsed, run=fake_run)
    assert attrib["listener_found"] is False
    assert attrib["owners"] == []


class AnyReturn:
    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_listener_attribution_returns_owner() -> None:
    netstat_txt = "\nTCP    127.0.0.1:7890    0.0.0.0:0    LISTENING    8420\n"
    ps_json = (
        '{"CommandLine":"clash.exe --foo","ExecutablePath":"C:\\\\Cl\\\\clash.exe",'
        '"ParentProcessId":1,"Caption":"clash.exe"}'
    )

    def fake_run(cmd: object, **_kwargs: object) -> AnyReturn:
        argv = tuple(cmd) if isinstance(cmd, (list, tuple)) else ()
        joined = " ".join(str(x) for x in argv).lower()
        if "powershell" in joined:
            return AnyReturn(0, ps_json, "")
        if "netstat" in joined:
            return AnyReturn(0, netstat_txt, "")
        if joined.startswith("tasklist"):
            return AnyReturn(0, '"clash.exe","8420"\r\n', "")
        return AnyReturn(1, "", "")

    from src.proxy_guard.localhost_attribution import build_localhost_proxy_attribution

    reg = ProxyRegistrySnapshot(1, "127.0.0.1:7890", None, None, None)
    parsed = parse_proxy_server(reg.proxy_server)
    attrib = build_localhost_proxy_attribution(reg, parsed, run=fake_run)
    assert attrib["listener_found"] is True
    assert attrib["owners"][0].get("pid") == 8420


def test_snapshot_serialization_roundtrip(tmp_path: Path) -> None:
    cap = WinInetCapturedState(
        snapshot_id="snap-abc",
        captured_at_utc="2026-05-02T12:00:00+00:00",
        values={
            "ProxyEnable": 1,
            "ProxyServer": "127.0.0.1:1",
            "AutoConfigURL": None,
            "AutoDetect": None,
            "ProxyOverride": None,
        },
        presence={
            "ProxyEnable": True,
            "ProxyServer": True,
            "AutoConfigURL": False,
            "AutoDetect": False,
            "ProxyOverride": False,
        },
    )
    plan = build_rollback_plan(cap)
    row = merge_snapshot_payload(cap, plan)
    path = append_proxy_snapshots_jsonl(tmp_path, row)
    loaded = load_snapshot_record_by_id(path, "snap-abc")
    assert loaded is not None
    assert loaded["snapshot_id"] == "snap-abc"
    assert loaded["values"]["ProxyEnable"] == 1


def test_rollback_planning_and_restore_argv() -> None:
    cap = WinInetCapturedState(
        snapshot_id="x",
        captured_at_utc="t",
        values={
            "ProxyEnable": 1,
            "ProxyServer": "127.0.0.1:9",
            "AutoConfigURL": None,
            "AutoDetect": 0,
            "ProxyOverride": None,
        },
        presence={
            "ProxyEnable": True,
            "ProxyServer": True,
            "AutoConfigURL": False,
            "AutoDetect": True,
            "ProxyOverride": False,
        },
    )
    plan = build_rollback_plan(cap)
    assert plan["snapshot_id"] == "x"
    argv = build_restore_reg_argv(cap)
    assert argv[0][0] == "reg"


def test_rollback_argv_delete_when_values_absent() -> None:
    cap = WinInetCapturedState(
        snapshot_id="",
        captured_at_utc="",
        values={k: None for k in ("ProxyEnable", "ProxyServer", "AutoConfigURL", "AutoDetect", "ProxyOverride")},
        presence={n: False for n in ("ProxyEnable", "ProxyServer", "AutoConfigURL", "AutoDetect", "ProxyOverride")},
    )
    argv = build_restore_reg_argv(cap)
    assert all(a[1] == "delete" for a in argv)


def test_verification_success_and_failure() -> None:
    assert verify_proxy_disabled(ProxyRegistrySnapshot(0, None, None, None, None)).ok is True
    assert verify_proxy_disabled(ProxyRegistrySnapshot(1, None, None, None, None)).ok is False
    assert verify_proxy_disabled(ProxyRegistrySnapshot(None, None, None, None, None)).ok is False


def test_failure_blocks_localhost_dead_port_vs_enabled() -> None:
    parsed = parse_proxy_server("127.0.0.1:7890").to_dict()
    dead = {"listener_found": False, "attribution_method": "netstat"}
    live = {"listener_found": True, "attribution_method": "netstat"}

    fb_dead = build_proxy_failure_blocks(proxy_enable=1, parsed_proxy_dict=parsed, localhost_attribution=dead)
    ids_dead = [b.failure_id for b in fb_dead]
    assert "wininet.localhost_proxy.dead_port" in ids_dead
    assert "wininet.localhost_proxy.enabled" not in ids_dead

    fb_live = build_proxy_failure_blocks(proxy_enable=1, parsed_proxy_dict=parsed, localhost_attribution=live)
    ids_live = [b.failure_id for b in fb_live]
    assert "wininet.localhost_proxy.dead_port" not in ids_live
    assert "wininet.localhost_proxy.enabled" in ids_live

    fb_unknown = build_proxy_failure_blocks(proxy_enable=1, parsed_proxy_dict=parsed, localhost_attribution=None)
    assert any(b.failure_id == "wininet.localhost_proxy.enabled" for b in fb_unknown)


def test_proxy_disable_writes_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "logs").mkdir(parents=True)

    reg_before = ProxyRegistrySnapshot(1, "127.0.0.1:9", None, None, None)
    reg_after = ProxyRegistrySnapshot(0, "127.0.0.1:9", None, None, None)
    counter = {"i": 0}

    def fake_read(**_k: object) -> ProxyRegistrySnapshot:
        i = counter["i"]
        counter["i"] += 1
        return reg_before if i == 0 else reg_after

    cap = WinInetCapturedState(
        snapshot_id="snap-fixture",
        captured_at_utc="t",
        values={k: None for k in ("ProxyEnable", "ProxyServer", "AutoConfigURL", "AutoDetect", "ProxyOverride")},
        presence={k: True for k in ("ProxyEnable", "ProxyServer", "AutoConfigURL", "AutoDetect", "ProxyOverride")},
    )

    def fake_capture(*, run: object, snapshot_id: str | None = None) -> WinInetCapturedState:
        return cap

    m1 = ProxyDisableMutation(argv=("reg", "add"), human="h")

    def fake_apply(_muts: object, *, dry_run: bool) -> tuple[Any, ...]:
        class R:
            argv = ("reg",)
            returncode = 0
            stderr = ""
            stdout = ""

        return (R(),)

    monkeypatch.setattr("src.command_handlers.read_proxy_registry", fake_read)
    monkeypatch.setattr("src.command_handlers.capture_wininet_snapshot", fake_capture)
    monkeypatch.setattr(
        "src.command_handlers.build_user_proxy_disable_mutations",
        lambda **_: ((m1,), ("line",)),
    )
    monkeypatch.setattr("src.command_handlers.summarize_mutations_plaintext", lambda _m: "argv")
    monkeypatch.setattr("src.command_handlers.apply_mutations", fake_apply)
    monkeypatch.setattr(
        "src.command_handlers.append_proxy_snapshots_jsonl",
        lambda _repo, _row: _repo / "logs" / "proxy_snapshots.jsonl",
    )

    written: list[dict[str, object]] = []

    def capture_audit(_path: Path, payload: dict[str, object]) -> None:
        written.append(dict(payload))

    monkeypatch.setattr("src.command_handlers.append_jsonl_core", capture_audit)
    monkeypatch.setattr("builtins.input", lambda _: "DISABLE_PROXY")

    from src.command_handlers import cmd_proxy_disable

    args = Namespace(repo_root=repo, dry_run=False, clear_server=False)
    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: repo)

    exit_code = cmd_proxy_disable(args)
    assert exit_code == 0
    assert written and written[0].get("snapshot_id") == "snap-fixture"
    assert isinstance(written[0].get("verification_result"), dict)


def test_proxy_diagnose_skip_probe_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.command_handlers import cmd_proxy_diagnose

    monkeypatch.setattr(
        "src.command_handlers.read_proxy_registry",
        lambda **_: ProxyRegistrySnapshot(1, "", None, None, None),
    )
    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: Path("."))

    buf = io.StringIO()

    def fake_print(*args: object, **kwargs: object) -> None:
        sep = str(kwargs.get("sep", " "))
        end = str(kwargs.get("end", "\n"))
        buf.write(sep.join(str(a) for a in args))
        buf.write(end)

    with patch("builtins.print", fake_print):
        rc = cmd_proxy_diagnose(Namespace(emit_json=True, repo_root=None, skip_listener_probe=True))
    assert rc == 0
    payload = json.loads(buf.getvalue().strip())
    assert payload["artifact"] == "proxy_diagnose"
    assert payload["localhost_attribution"] is None


def test_proxy_rollback_unknown_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir(parents=True)
    import src.command_handlers as ch

    err = io.StringIO()
    with patch("sys.stderr", err):
        rc = ch.cmd_proxy_rollback(
            Namespace(snapshot_id="nonexistent", dry_run=True, repo_root=tmp_path),
        )
    assert rc == 2


def test_proxy_disable_verification_warning_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "logs").mkdir(parents=True)

    reg_before = ProxyRegistrySnapshot(1, None, None, None, None)
    reg_still_on = ProxyRegistrySnapshot(1, None, None, None, None)
    idx = {"n": 0}

    def fake_read(**_k: object) -> ProxyRegistrySnapshot:
        i = idx["n"]
        idx["n"] += 1
        return reg_before if i == 0 else reg_still_on

    _keys = ("ProxyEnable", "ProxyServer", "AutoConfigURL", "AutoDetect", "ProxyOverride")
    cap = WinInetCapturedState(
        snapshot_id="snap-2",
        captured_at_utc="t",
        values={k: None for k in _keys},
        presence={k: False for k in _keys},
    )

    monkeypatch.setattr("src.command_handlers.read_proxy_registry", fake_read)
    monkeypatch.setattr("src.command_handlers.capture_wininet_snapshot", lambda **_: cap)
    m1 = ProxyDisableMutation(argv=("reg",), human="h")
    monkeypatch.setattr(
        "src.command_handlers.build_user_proxy_disable_mutations",
        lambda **_: ((m1,), ("h",)),
    )
    monkeypatch.setattr("src.command_handlers.summarize_mutations_plaintext", lambda _: "x")

    class R:
        argv = ("reg",)
        returncode = 0
        stderr = ""
        stdout = ""

    monkeypatch.setattr("src.command_handlers.apply_mutations", lambda _m, dry_run=False: (R(),))
    monkeypatch.setattr("src.command_handlers.append_jsonl_core", lambda *_a, **_k: None)
    monkeypatch.setattr("builtins.input", lambda _: "DISABLE_PROXY")
    monkeypatch.setattr("src.command_handlers._repo_root", lambda _p=None: repo)

    err = io.StringIO()
    from src.command_handlers import cmd_proxy_disable

    with patch("sys.stderr", err):
        ec = cmd_proxy_disable(Namespace(repo_root=repo, dry_run=False, clear_server=False))
    assert ec == 1
    assert "WARNING" in err.getvalue()
