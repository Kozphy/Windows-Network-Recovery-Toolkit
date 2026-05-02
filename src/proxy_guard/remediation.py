"""Structured ``reg.exe`` argv previews for disabling WinINET user proxy keys.

WinHTTP reset stays out-of-scope deliberately; callers must document that externally.
"""

from __future__ import annotations

from dataclasses import dataclass

INTERNET_SETTINGS_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_INTERNET_SETTINGS_KEY = INTERNET_SETTINGS_KEY


CONFIRMATION_PHRASE = "DISABLE_PROXY"


@dataclass(frozen=True)
class ProxyDisableMutation:
    """Single ``reg.exe`` invocation (argument vector, no shell)."""

    argv: tuple[str, ...]
    human: str


def build_user_proxy_disable_mutations(*, clear_proxy_server_value: bool) -> tuple[tuple[ProxyDisableMutation, ...], tuple[str, ...]]:
    """Preview WinINET HKCU disables: ``ProxyEnable=0`` plus optional ``ProxyServer`` deletion.

    WinHTTP remains untouched deliberately.
    """
    lines: list[str] = []
    mutations: list[ProxyDisableMutation] = []

    m1 = ProxyDisableMutation(
        argv=(
            "reg",
            "add",
            _INTERNET_SETTINGS_KEY,
            "/v",
            "ProxyEnable",
            "/t",
            "REG_DWORD",
            "/d",
            "0",
            "/f",
        ),
        human=f'reg add "{_INTERNET_SETTINGS_KEY}" /v ProxyEnable /t REG_DWORD /d 0 /f',
    )
    mutations.append(m1)
    lines.append(m1.human)

    if clear_proxy_server_value:
        m2 = ProxyDisableMutation(
            argv=(
                "reg",
                "delete",
                _INTERNET_SETTINGS_KEY,
                "/v",
                "ProxyServer",
                "/f",
            ),
            human=f'reg delete "{_INTERNET_SETTINGS_KEY}" /v ProxyServer /f',
        )
        mutations.append(m2)
        lines.append(m2.human)

    warnings = (
        "This modifies only HKCU WinINET proxy values; WinHTTP is unchanged.",
        "Software that reapplies proxy policy may restore these keys after logout or schedule.",
    )
    return tuple(mutations), tuple(lines + list(warnings))
