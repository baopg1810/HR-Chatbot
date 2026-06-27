from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.base import BaseRepository
from app.models.user import User
from app.core.security import get_password_hash

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        role: str = "employee",
        role_access: Optional[str] = None,
        employee_code: Optional[str] = None,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        department_id: Optional[Any] = None,
        position: Optional[str] = None,
        employment_type: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        # Resolve roles and departments for backward compatibility
        resolved_role = role
        if role_access is not None:
            if role_access == "admin":
                resolved_role = "admin"
            elif role_access == "department_admin" or role_access == "hr_admin" or role_access == "hr":
                resolved_role = "hr"
            else:
                resolved_role = "employee"

        resolved_dept = department
        if department_id is not None:
            resolved_dept = str(department_id)

        db_obj = User(
            email=email,
            role=resolved_role,
            password_hash=get_password_hash(password),
            employee_code=employee_code,
            full_name=full_name,
            department=resolved_dept,
            position=position,
            employment_type=employment_type,
            is_active=is_active
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

user_repository = UserRepository(User)

