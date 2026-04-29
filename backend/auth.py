import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException
from jose import JWTError, jwt


@dataclass
class AuthUser:
    user_id: str
    email: str


def _decode_supabase_jwt(token: str) -> dict:
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_JWT_SECRET is not configured.",
        )
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {exc}") from exc


def get_current_user(authorization: Optional[str] = Header(default=None)) -> AuthUser:
    # Optional local bypass for rapid development.
    if os.getenv("AUTH_BYPASS_USER_ID"):
        return AuthUser(
            user_id=os.environ["AUTH_BYPASS_USER_ID"],
            email=os.getenv("AUTH_BYPASS_EMAIL", "dev@example.com"),
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    payload = _decode_supabase_jwt(token)
    user_id = payload.get("sub")
    email = payload.get("email") or payload.get("user_email") or "unknown@example.com"
    if not user_id:
        raise HTTPException(status_code=401, detail="JWT missing subject (sub).")
    return AuthUser(user_id=user_id, email=email)
