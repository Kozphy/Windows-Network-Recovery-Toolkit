from __future__ import annotations

from platform_core.privacy import (
    redact_text,
    sanitize_domain,
    sanitize_ip,
    sanitize_hostname,
    sanitize_username,
    stable_endpoint_hash,
)


def test_stable_endpoint_hash_stable() -> None:
    h1 = stable_endpoint_hash("HOST-A", "10.1", None)
    h2 = stable_endpoint_hash("HOST-A", "10.1", None)
    assert h1 == h2
    assert len(h1) == 32


def test_sanitize_private_ipv4() -> None:
    assert sanitize_ip("192.168.1.42") == "192.168.x.x"
    assert sanitize_ip("10.20.30.40") == "10.x.x.x"
    assert sanitize_ip("127.0.0.1") == "127.0.0.1"


def test_allowlist_public_domain() -> None:
    assert sanitize_domain("GOOGLE.COM") == "google.com"


def test_hostname_username_not_raw() -> None:
    assert "corp-laptop" not in sanitize_hostname("corp-laptop")
    assert sanitize_username("jdoe") == "user_redacted"


def test_redact_user_path() -> None:
    raw = r"C:\\Users\\alice\\corp\\x.exe hits 192.168.44.12"
    r2 = redact_text(raw)
    assert "alice" not in r2.lower()
    assert "192.168.x.x" in r2

