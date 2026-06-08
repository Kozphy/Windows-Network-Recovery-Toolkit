from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from platform_core.settings import PlatformSettings
from platform_core.startup_checks import run_startup_checks


def test_startup_checks_pass_with_temp_data_dir(tmp_path: Path) -> None:
    settings = PlatformSettings(platform_data_dir=tmp_path)
    report = run_startup_checks(settings)
    assert report.ok is True
    names = {c.name for c in report.checks}
    assert "filesystem" in names
    assert "configuration" in names


def test_startup_checks_fail_when_data_dir_not_writable(tmp_path: Path) -> None:
    settings = PlatformSettings(platform_data_dir=tmp_path / "nested")

    def _raise_mkdir(*args: object, **kwargs: object) -> None:
        raise OSError("permission denied")

    with patch.object(Path, "mkdir", _raise_mkdir):
        report = run_startup_checks(settings)
    assert report.ok is False
    fs = next(c for c in report.checks if c.name == "filesystem")
    assert fs.status == "failed"
