from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]


def _disabled_principal() -> Principal:
    roles = frozenset({"requester", "approver", "verifier", "auditor"})
    return Principal(subject=os.getenv("DI_DEV_SUBJECT", "dev-user"), roles=roles)


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    mode = os.getenv("DI_AUTH_MODE", "disabled").lower()
    if mode == "disabled":
        return _disabled_principal()
    if mode != "jwt":
        raise HTTPException(status_code=500, detail="unsupported DI_AUTH_MODE")
    if credentials is None:
        raise HTTPException(status_code=401, detail="bearer token required")

    secret = os.getenv("DI_JWT_SECRET")
    issuer = os.getenv("DI_JWT_ISSUER")
    audience = os.getenv("DI_JWT_AUDIENCE")
    if not secret or not issuer or not audience:
        raise HTTPException(status_code=500, detail="JWT auth is not fully configured")

    try:
        claims = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=[os.getenv("DI_JWT_ALGORITHM", "HS256")],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc

    raw_roles = claims.get("roles", [])
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    return Principal(subject=str(claims["sub"]), roles=frozenset(map(str, raw_roles)))


def require_role(role: str):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if role not in principal.roles:
            raise HTTPException(status_code=403, detail=f"role required: {role}")
        return principal

    return dependency
