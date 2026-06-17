from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import Header, HTTPException, status

from src.config import get_settings
from src.models.schemas import User
from src.services.demo_users import get_demo_user


ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
DEFAULT_ACCESS_TOKEN_SECONDS = 3600
DEFAULT_REFRESH_TOKEN_SECONDS = 60 * 60 * 24 * 30


@dataclass
class RefreshTokenRecord:
    user_id: str
    expires_at: int


_ACTIVE_REFRESH_TOKENS: dict[str, RefreshTokenRecord] = {}


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(data: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), data.encode("ascii"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _jwt_secret() -> str:
    settings = get_settings()
    return settings.jwt_secret


def _create_token(user: User, token_type: str, expires_in_seconds: int, jti: str | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department_id": user.department_id,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    if jti is not None:
        payload["jti"] = jti
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = _sign(signing_input, _jwt_secret())
    return f"{signing_input}.{signature}"


def create_access_token(user: User, expires_in_seconds: int = DEFAULT_ACCESS_TOKEN_SECONDS) -> str:
    return _create_token(user, ACCESS_TOKEN_TYPE, expires_in_seconds)


def create_refresh_token(user: User, expires_in_seconds: int = DEFAULT_REFRESH_TOKEN_SECONDS) -> str:
    token = _create_token(user, REFRESH_TOKEN_TYPE, expires_in_seconds, jti=str(uuid4()))
    payload = _decode_token_payload(token)
    _ACTIVE_REFRESH_TOKENS[token] = RefreshTokenRecord(
        user_id=user.id,
        expires_at=int(payload["exp"]),
    )
    return token


def issue_token_pair(user: User) -> tuple[str, str]:
    return create_access_token(user), create_refresh_token(user)


def _decode_token_payload(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
    except ValueError as exc:
        raise _auth_error("Invalid token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = _sign(signing_input, _jwt_secret())
    if not hmac.compare_digest(signature, expected_signature):
        raise _auth_error("Invalid token")

    try:
        payload = json.loads(_base64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise _auth_error("Invalid token") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise _auth_error("Token expired")

    return payload


def verify_access_token(token: str) -> User:
    payload = _decode_token_payload(token)
    if payload.get("type", ACCESS_TOKEN_TYPE) != ACCESS_TOKEN_TYPE:
        raise _auth_error("Refresh token cannot be used as access token")
    return _user_from_token_payload(payload)


def refresh_token_pair(refresh_token: str) -> tuple[str, str]:
    payload = _decode_token_payload(refresh_token)
    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise _auth_error("Expected refresh token")

    record = _ACTIVE_REFRESH_TOKENS.get(refresh_token)
    if record is None:
        raise _auth_error("Refresh token revoked or unknown")
    if record.expires_at < int(time.time()):
        _ACTIVE_REFRESH_TOKENS.pop(refresh_token, None)
        raise _auth_error("Refresh token expired")

    user = _user_from_token_payload(payload)
    revoke_refresh_token(refresh_token)
    return issue_token_pair(user)


def revoke_refresh_token(refresh_token: str) -> bool:
    return _ACTIVE_REFRESH_TOKENS.pop(refresh_token, None) is not None


def reset_refresh_token_store() -> None:
    _ACTIVE_REFRESH_TOKENS.clear()


def _user_from_token_payload(payload: dict[str, Any]) -> User:
    user = get_demo_user(str(payload.get("sub", "")))
    if user is None:
        user = _user_from_payload(payload)
    return user


def user_from_authorization_header(authorization: str | None) -> User:
    if not authorization:
        raise _auth_error("Missing bearer token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _auth_error("Missing bearer token")
    return verify_access_token(token)


async def get_current_user(authorization: str | None = Header(default=None)) -> User:
    return user_from_authorization_header(authorization)


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_payload(payload: dict[str, Any]) -> User:
    try:
        return User(
            id=str(payload["sub"]),
            email=str(payload["email"]),
            full_name=str(payload.get("full_name") or payload["email"]),
            role=payload["role"],
            department_id=payload.get("department_id"),
        )
    except (KeyError, ValueError) as exc:
        raise _auth_error("Unknown user") from exc
