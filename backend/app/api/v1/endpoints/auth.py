from datetime import datetime, timezone
import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.database.session import get_db
from app.repository.user import user_repository
from app.repository.refresh_token import refresh_token_repository
from app.schemas.auth import UserLogin, Token, UserResponse, UserCreateByAdmin, TokenRefreshRequest, LogoutRequest
from app.models.user import User

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    request: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user by email and password, and return JWT access and refresh tokens.
    """
    # Fetch user by email
    user = await user_repository.get_by_email(db, email=request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if password_hash exists
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has no password set. Please reset your password."
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create tokens
    access_token = create_access_token(subject=user)
    refresh_token = create_refresh_token(subject=user)
    
    # Parse refresh token expiration time
    payload = decode_token(refresh_token)
    exp_timestamp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)
    
    # Save refresh token to DB
    await refresh_token_repository.create_token(
        db,
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh JWT access and refresh tokens using a valid, active refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    # Retrieve refresh token from DB
    db_token = await refresh_token_repository.get_by_token(db, token=request.refresh_token)
    if not db_token:
        raise credentials_exception
    
    # Verify signature and payload
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise credentials_exception

    # Check if expired in DB or in token itself
    db_token_expires = db_token.expires_at if db_token.expires_at.tzinfo else db_token.expires_at.replace(tzinfo=timezone.utc)
    if db_token_expires < datetime.now(timezone.utc):
        await refresh_token_repository.revoke_token(db, token=request.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
        
    # Generate new tokens (Token Rotation)
    user = await user_repository.get(db, id=uuid.UUID(str(user_id)))
    new_access_token = create_access_token(subject=user)
    new_refresh_token = create_refresh_token(subject=user)
    
    # Parse new refresh token expiration
    new_payload = decode_token(new_refresh_token)
    new_exp_timestamp = new_payload.get("exp")
    new_expires_at = datetime.fromtimestamp(new_exp_timestamp, tz=timezone.utc).replace(tzinfo=None)
    
    # Revoke old refresh token
    await refresh_token_repository.revoke_token(db, token=request.refresh_token)
    
    # Save new refresh token
    await refresh_token_repository.create_token(
        db,
        user_id=uuid.UUID(str(user_id)),
        token=new_refresh_token,
        expires_at=new_expires_at
    )
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=user
    )

@router.post("/logout")
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Log out a user by revoking their refresh token.
    """
    revoked = await refresh_token_repository.revoke_token(db, token=request.refresh_token)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token already revoked or invalid"
        )
    return {"ok": True, "message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the authenticated user's profile information.
    """
    return current_user

@router.post("/users", response_model=UserResponse)
async def create_user_by_admin(
    request: UserCreateByAdmin,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user. Access restricted to admin users only.
    """
    if current_user.role_access != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to perform this action"
        )
    
    # Check if user already exists
    existing_user = await user_repository.get_by_email(db, email=request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    new_user = await user_repository.create(
        db,
        email=request.email,
        password=request.password,
        role_access=request.role_access,
        department_id=request.department_id
    )
    return new_user
