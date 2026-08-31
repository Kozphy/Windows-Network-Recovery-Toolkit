from pathlib import Path


def test_fix_wininet_proxy_uses_repo_launcher() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "fix-wininet-proxy.cmd"
    text = script.read_text(encoding="utf-8")

    assert (
        '"%PYTHON%" "%~dp0run_src.py" proxy-fix --confirm DISABLE_WININET_PROXY --dry-run false'
        in text
    )
    assert '"%PYTHON%" -m src' not in text
