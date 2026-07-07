from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.telegram import TelegramUserLink
from app.models.user import User
from app.repository.user import user_repository


async def authenticate_and_link_telegram_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> TelegramUserLink | None:
    user = await user_repository.get_by_email(db, email=email)
    if user is None or not user.is_active or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return await upsert_telegram_link(
        db,
        user=user,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )


async def upsert_telegram_link(
    db: AsyncSession,
    *,
    user: User,
    telegram_user_id: int,
    telegram_chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> TelegramUserLink:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(TelegramUserLink).where(
            (TelegramUserLink.telegram_user_id == telegram_user_id)
            | (TelegramUserLink.telegram_chat_id == telegram_chat_id)
        )
    )
    link = result.scalars().first()
    if link is None:
        link = TelegramUserLink(
            user_id=user.id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
        )
        db.add(link)
    else:
        link.user_id = user.id
        link.telegram_user_id = telegram_user_id
        link.telegram_chat_id = telegram_chat_id

    link.username = username
    link.first_name = first_name
    link.last_name = last_name
    link.is_active = True
    link.last_seen_at = now
    link.updated_at = now
    await db.commit()
    await db.refresh(link)
    return link


async def get_active_link_by_chat_id(db: AsyncSession, telegram_chat_id: int) -> TelegramUserLink | None:
    result = await db.execute(
        select(TelegramUserLink).where(
            TelegramUserLink.telegram_chat_id == telegram_chat_id,
            TelegramUserLink.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def list_active_telegram_links(db: AsyncSession) -> list[TelegramUserLink]:
    result = await db.execute(select(TelegramUserLink).where(TelegramUserLink.is_active.is_(True)))
    return list(result.scalars().all())


async def deactivate_telegram_link(db: AsyncSession, telegram_chat_id: int) -> bool:
    link = await get_active_link_by_chat_id(db, telegram_chat_id)
    if link is None:
        return False
    link.is_active = False
    link.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def touch_telegram_link(db: AsyncSession, link: TelegramUserLink) -> None:
    link.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
