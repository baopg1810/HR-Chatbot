import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from app.core.config import get_settings

settings = get_settings()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its bcrypt hashed version.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    
    subject_id = getattr(subject, "id", subject)
    email = getattr(subject, "email", None)
    role = getattr(subject, "role", None)
    if role is None:
        role = getattr(subject, "role_access", None)
    department_id = getattr(subject, "department_id", None)

    to_encode = {
        "exp": expire,
        "sub": str(subject_id),
        "iat": datetime.now(timezone.utc)
    }
    if email:
        to_encode["email"] = email
    if role:
        to_encode["role"] = role
    if department_id:
        to_encode["department_id"] = str(department_id)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt

def create_refresh_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT refresh token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default refresh token expiry: 30 days
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    
    subject_id = getattr(subject, "id", subject)
    email = getattr(subject, "email", None)
    role = getattr(subject, "role", None)
    if role is None:
        role = getattr(subject, "role_access", None)
    department_id = getattr(subject, "department_id", None)

    to_encode = {
        "exp": expire,
        "sub": str(subject_id),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }
    if email:
        to_encode["email"] = email
    if role:
        to_encode["role"] = role
    if department_id:
        to_encode["department_id"] = str(department_id)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode a JWT token. Raises jwt.PyJWTError if invalid/expired.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )
