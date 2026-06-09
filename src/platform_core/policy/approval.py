"""Human approval token validation."""

from __future__ import annotations

import secrets


def generate_approval_token() -> str:
    return secrets.token_hex(16)


def validate_approval_token(provided: str, expected: str) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided.strip(), expected.strip())
