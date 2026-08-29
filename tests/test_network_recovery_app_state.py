"""Deterministic tests for bounded ChatGPT process/network-state recovery evidence."""

from __future__ import annotations

from pathlib import Path

from src.network_recovery.app_state import (
    NETWORK_STATE_FILENAME,
    discover_chatgpt_network_state_files,
    observe_chatgpt_network_state,
    parse_tasklist_process_count,
    quarantine_network_state_files,
)


def _fixture_state(tmp_path: Path) -> tuple[dict[str, str], Path]:
    env = {
        "APPDATA": str(tmp_path / "Roaming"),
        "LOCALAPPDATA": str(tmp_path / "Local"),
    }
    state = Path(env["APPDATA"]) / "ChatGPT" / "Network" / NETWORK_STATE_FILENAME
    state.parent.mkdir(parents=True)
    state.write_text('{"quic": "fixture-only"}', encoding="utf-8")
    return env, state


def test_tasklist_parser_counts_99_exact_chatgpt_rows() -> None:
    rows = [f'"ChatGPT.exe","{pid}","Console","1","10,000 K"' for pid in range(1, 100)]
    rows.append('"NotChatGPT.exe","100","Console","1","10,000 K"')
    assert parse_tasklist_process_count("\n".join(rows)) == 99


def test_network_state_observation_is_bounded_and_metadata_only(tmp_path: Path) -> None:
    env, state = _fixture_state(tmp_path)
    unrelated = tmp_path / "Unrelated" / "Network" / NETWORK_STATE_FILENAME
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("do not touch", encoding="utf-8")

    files = discover_chatgpt_network_state_files(env=env)
    observed = observe_chatgpt_network_state(env=env)

    assert files == [state]
    assert observed["file_count"] == 1
    assert observed["content_read"] is False
    assert observed["locations"] == [r"%APPDATA%\ChatGPT\Network\Network Persistent State"]
    assert unrelated.is_file()


def test_quarantine_is_reversible_and_does_not_delete(tmp_path: Path) -> None:
    env, state = _fixture_state(tmp_path)
    rows = quarantine_network_state_files([state], env=env, timestamp="20260829T000000Z")

    assert rows[0]["status"] == "quarantined"
    assert not state.exists()
    backup = state.with_name(f"{NETWORK_STATE_FILENAME}.wnrt-backup-20260829T000000Z")
    assert backup.read_text(encoding="utf-8") == '{"quic": "fixture-only"}'


def test_quarantine_blocks_same_named_file_outside_known_roots(tmp_path: Path) -> None:
    env, _state = _fixture_state(tmp_path)
    outside = tmp_path / "OtherApp" / NETWORK_STATE_FILENAME
    outside.parent.mkdir(parents=True)
    outside.write_text("preserve", encoding="utf-8")

    rows = quarantine_network_state_files([outside], env=env, timestamp="20260829T000000Z")

    assert rows[0]["status"] == "blocked"
    assert outside.read_text(encoding="utf-8") == "preserve"
