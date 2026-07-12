"""Shared Startup-folder hook helpers for proxy drift automation."""

from __future__ import annotations

import os
from pathlib import Path


def startup_folder() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_hook_path(name: str) -> Path:
    return startup_folder() / f"{name}.cmd"


def write_startup_hook(*, name: str, lines: list[str]) -> Path:
    path = startup_hook_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def remove_startup_hook(name: str) -> bool:
    path = startup_hook_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True
