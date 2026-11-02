"""Admin authentication: bcrypt password hashes and short-lived HS256 JWTs."""
from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=4))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], (hashed or "").encode() or _DUMMY_HASH)
    except ValueError:
        return False


def authenticate(settings: Settings, username: str, password: str) -> bool:
    """Constant-effort check: the bcrypt comparison always runs, even for a wrong username."""
    user_ok = hmac.compare_digest(username.encode(), settings.admin_username.encode())
    pw_ok = verify_password(password, settings.admin_password_hash if user_ok else None)
    return user_ok and pw_ok


def create_token(settings: Settings, subject: str, role: str = "admin") -> tuple[str, int]:
    expires = timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": subject, "role": role, "iat": now, "exp": now + expires}, settings.jwt_secret, algorithm="HS256")
    return token, int(expires.total_seconds())


def require_admin(creds: HTTPAuthorizationCredentials | None = Depends(_bearer), settings: Settings = Depends(get_settings)) -> str:
    if not settings.jwt_secret:
        raise HTTPException(status_code=503, detail="Admin access is not configured on this server.")
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.", headers={"WWW-Authenticate": "Bearer"})
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to do that.")
    return str(payload["sub"])
