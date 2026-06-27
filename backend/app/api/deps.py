import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.repository.user import user_repository
from app.models.user import User
from app.core.security import decode_token
from app.core.config import get_settings

security = HTTPBearer()
settings = get_settings()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    return await get_current_user_from_token(credentials.credentials, db)


async def get_current_user_from_authorization_header(
    authorization: str | None,
    db: AsyncSession,
) -> User:
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
    return await get_current_user_from_token(token, db)


async def get_current_user_from_token(token: str, db: AsyncSession) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = None
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        # Ensure it's not a refresh token being used as an access token
        if payload.get("type") == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used as access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            if settings.app_env == "production":
                raise credentials_exception
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, user_id_str)
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = None
    try:
        user = await user_repository.get(db, id=user_id)
    except Exception:
        pass

    if user is not None and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    if user is None and settings.app_env != "production":
        email = payload.get("email")
        role = payload.get("role")
        if email and role:
            role_access = "admin" if role == "hr_admin" else role
            user = User(
                email=email,
                role_access=role_access,
            )
            user.id = user_id
            dept_id = payload.get("department_id")
            if dept_id:
                try:
                    user.department_id = uuid.UUID(dept_id)
                except ValueError:
                    user.department_id = dept_id
        else:
            raise credentials_exception

    if user is None:
        raise credentials_exception
        
    return user

