import datetime
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.base import BaseRepository
from app.models.refresh_token import RefreshToken

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    async def create_token(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        token: str,
        expires_at: datetime.datetime
    ) -> RefreshToken:
        db_obj = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        result = await db.execute(select(RefreshToken).filter(RefreshToken.token == token))
        return result.scalars().first()

    async def revoke_token(self, db: AsyncSession, token: str) -> bool:
        db_token = await self.get_by_token(db, token)
        if db_token:
            await db.delete(db_token)
            await db.commit()
            return True
        return False

refresh_token_repository = RefreshTokenRepository(RefreshToken)
