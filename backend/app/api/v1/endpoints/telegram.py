from __future__ import annotations

import re
import unicodedata
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat import run_chat_for_user
from app.core.config import get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.schemas import ChatRequest
from app.services.telegram import format_chat_response_for_telegram, send_telegram_message
from app.services.telegram_links import (
    authenticate_and_link_telegram_user,
    deactivate_telegram_link,
    get_active_link_by_chat_id,
    touch_telegram_link,
)

router = APIRouter()


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return {"ok": True}

    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = sender.get("id")
    if not text or chat_id is None or telegram_user_id is None:
        return {"ok": True}

    chat_id = int(chat_id)
    telegram_user_id = int(telegram_user_id)
    if text.startswith("/start"):
        await send_telegram_message(chat_id, _start_message())
        return {"ok": True}
    if text.startswith("/login"):
        await _handle_login_command(db, text, chat_id=chat_id, telegram_user_id=telegram_user_id, sender=sender)
        return {"ok": True}
    if text.startswith("/logout"):
        await deactivate_telegram_link(db, chat_id)
        await send_telegram_message(chat_id, "Đã đăng xuất Telegram khỏi HR Assistant.")
        return {"ok": True}
    link = await get_active_link_by_chat_id(db, chat_id)
    if link is None:
        await send_telegram_message(chat_id, "Bạn cần đăng nhập trước. Gõ: /login email@example.com mật_khẩu")
        return {"ok": True}

    user = await db.get(User, link.user_id)
    if user is None or not user.is_active:
        await deactivate_telegram_link(db, chat_id)
        await send_telegram_message(chat_id, "Tài khoản liên kết không còn khả dụng. Vui lòng /login lại.")
        return {"ok": True}
    if _looks_like_ticket_submit_confirmation(text):
        message = "Để xác nhận hoặc gửi yêu cầu, vui lòng mở HR Assistant"
        if settings.telegram_app_url:
            message += f": {settings.telegram_app_url}"
        await send_telegram_message(chat_id, message)
        return {"ok": True}

    await touch_telegram_link(db, link)
    response = await run_chat_for_user(
        user,
        ChatRequest(message=text, session_id=_telegram_session_id(chat_id)),
        session_id=_telegram_session_id(chat_id),
        message_id=f"msg-{uuid4()}",
        db=db,
    )
    await send_telegram_message(
        chat_id,
        format_chat_response_for_telegram(response, app_url=settings.telegram_app_url),
    )
    return {"ok": True}


async def _handle_login_command(
    db: AsyncSession,
    text: str,
    *,
    chat_id: int,
    telegram_user_id: int,
    sender: dict,
) -> None:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await send_telegram_message(chat_id, "Cú pháp: /login email@example.com mật_khẩu")
        return

    link = await authenticate_and_link_telegram_user(
        db,
        email=parts[1],
        password=parts[2],
        telegram_user_id=telegram_user_id,
        telegram_chat_id=chat_id,
        username=sender.get("username"),
        first_name=sender.get("first_name"),
        last_name=sender.get("last_name"),
    )
    if link is None:
        await send_telegram_message(chat_id, "Email hoặc mật khẩu không đúng.")
        return
    await send_telegram_message(chat_id, "Đăng nhập Telegram thành công. Bạn có thể hỏi HR Assistant ngay tại đây.")


def _telegram_session_id(chat_id: int) -> str:
    return f"session-{uuid5(NAMESPACE_URL, f'telegram:{chat_id}')}"


def _start_message() -> str:
    return (
        "Chào bạn, mình là HR Assistant trên Telegram.\n"
        "Đăng nhập bằng lệnh: /login email@example.com mật_khẩu\n"
        "Sau khi đăng nhập, bạn có thể hỏi về chính sách HR, nghỉ phép, bảo hiểm, phúc lợi và các chủ đề nội bộ."
    )


def _looks_like_ticket_submit_confirmation(text: str) -> bool:
    normalized = _normalize_text(text)
    return bool(
        re.fullmatch(r"(dong y|xac nhan|ok|oke|confirm|gui di|gui ticket)", normalized)
        or re.search(r"\b(dong y|xac nhan|confirm)\s+(gui|tao|submit)", normalized)
        or re.search(r"\b(gui|submit)\s+(ticket|yeu cau|phieu)\b", normalized)
    )


def _normalize_text(text: str) -> str:
    lowered = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", lowered)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
