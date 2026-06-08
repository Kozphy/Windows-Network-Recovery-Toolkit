from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.proxy_guard.linux_proxy_commands import cmd_proxy_linux_snapshot
from src.proxy_guard.linux_proxy_snapshot import (
    LinuxProxySnapshot,
    _parse_environment_file,
    _read_process_env,
    _scan_apt_proxy_conf,
    collect_linux_proxy_snapshot,
)


def test_read_process_env_normalizes_keys() -> None:
    env = {"HTTP_PROXY": "http://corp:8080", "no_proxy": "localhost"}
    assert _read_process_env(env) == {"HTTP_PROXY": "http://corp:8080", "no_proxy": "localhost"}


def test_parse_environment_file(tmp_path: Path) -> None:
    path = tmp_path / "environment"
    path.write_text(
        'HTTP_PROXY="http://proxy.local:3128"\nexport HTTPS_PROXY=http://proxy.local:3128\n',
        encoding="utf-8",
    )
    parsed = _parse_environment_file(path)
    assert parsed["HTTP_PROXY"] == "http://proxy.local:3128"
    assert parsed["HTTPS_PROXY"] == "http://proxy.local:3128"


def test_scan_apt_proxy_conf(tmp_path: Path) -> None:
    apt_dir = tmp_path / "apt.conf.d"
    apt_dir.mkdir()
    (apt_dir / "99proxy").write_text(
        'Acquire::http::Proxy "http://apt-proxy:3142";\n',
        encoding="utf-8",
    )
    lines = _scan_apt_proxy_conf(apt_dir)
    assert len(lines) == 1
    assert "Acquire::http::Proxy" in lines[0]


def test_collect_linux_proxy_snapshot_from_env_and_files(tmp_path: Path) -> None:
    etc_env = tmp_path / "environment"
    etc_env.write_text("http_proxy=http://etc:8080\n", encoding="utf-8")
    apt_dir = tmp_path / "apt"
    apt_dir.mkdir()

    snap = collect_linux_proxy_snapshot(
        env={"HTTPS_PROXY": "https://env:8443"},
        etc_environment_path=etc_env,
        apt_conf_dir=apt_dir,
        skip_optional_cli=True,
    )
    assert isinstance(snap, LinuxProxySnapshot)
    assert snap.environment["HTTPS_PROXY"] == "https://env:8443"
    assert snap.etc_environment["http_proxy"] == "http://etc:8080"
    assert snap.proxy_configured() is True
    payload = snap.to_jsonable()
    assert payload["proxy_configured"] is True
    assert "process_environment" in payload["sources"]


def test_proxy_configured_gsettings_manual_host() -> None:
    snap = LinuxProxySnapshot(
        captured_at_utc="2026-01-01T00:00:00Z",
        os_family="linux",
        linux_distro="ubuntu",
        wsl=False,
        environment={},
        etc_environment={},
        gsettings={
            "org.gnome.system.proxy/mode": "'manual'",
            "org.gnome.system.proxy.http/host": "'proxy.corp'",
        },
        networkmanager={},
        apt_proxy_lines=[],
    )
    assert snap.proxy_configured() is True


def test_cmd_proxy_linux_snapshot_json(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    monkeypatch.setattr(
        "src.proxy_guard.linux_proxy_commands.collect_linux_proxy_snapshot",
        lambda **_: LinuxProxySnapshot(
            captured_at_utc="2026-01-01T00:00:00Z",
            os_family="linux",
            linux_distro="ubuntu",
            wsl=False,
            environment={"HTTP_PROXY": "http://x:1"},
            etc_environment={},
            gsettings={},
            networkmanager={},
            apt_proxy_lines=[],
            sources=["process_environment"],
        ),
    )
    monkeypatch.setattr(
        "src.proxy_guard.linux_proxy_commands.platform.system",
        lambda: "Linux",
    )
    args = argparse.Namespace(emit_json=True, skip_optional_cli=True)
    rc = cmd_proxy_linux_snapshot(args)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["proxy_configured"] is True
