from __future__ import annotations
from typing import Any
from fastapi import Header, HTTPException, status
from app.core.security import decode_token
from app.models.user import User

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

async def get_current_user(authorization: str | None = Header(default=None)) -> User:
    return user_from_authorization_header(authorization)

def verify_access_token(token: str) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type", ACCESS_TOKEN_TYPE) != ACCESS_TOKEN_TYPE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used as access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        department_id = payload.get("department_id")
        
        role_access = "admin" if role == "hr_admin" else role
        user = User(
            email=email or "unknown@example.com",
            role_access=role_access or "user",
        )
        user.id = user_id
        if department_id:
            user.department_id = department_id
        return user
    except Exception as exc:
        msg = str(exc)
        if "expired" in msg.lower():
            detail = "Token expired"
        elif "signature" in msg.lower() or "decode" in msg.lower() or "invalid" in msg.lower():
            detail = "Invalid token"
        else:
            detail = "Could not validate credentials"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_access_token(user: Any, expires_in_seconds: int = 3600) -> str:
    from datetime import timedelta
    from app.core.security import create_access_token as cat
    return cat(user, expires_delta=timedelta(seconds=expires_in_seconds))

def create_refresh_token(user: Any, expires_in_seconds: int = 30 * 24 * 3600) -> str:
    from datetime import timedelta
    from app.core.security import create_refresh_token as crt
    return crt(user, expires_delta=timedelta(seconds=expires_in_seconds))

def issue_token_pair(user: Any) -> tuple[str, str]:
    return create_access_token(user), create_refresh_token(user)

def user_from_authorization_header(authorization: str | None) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(token)

def refresh_token_pair(refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != REFRESH_TOKEN_TYPE:
            raise HTTPException(status_code=401, detail="Expected refresh token")
        user_id = payload.get("sub")
        email = payload.get("email", "dummy@example.com")
        role = payload.get("role", "employee")
        user = User(email=email, role_access="admin" if role == "hr_admin" else role)
        user.id = user_id
        return issue_token_pair(user)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))

def revoke_refresh_token(refresh_token: str) -> bool:
    return True

def reset_refresh_token_store() -> None:
    pass
