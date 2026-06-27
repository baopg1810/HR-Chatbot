import uuid
import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base

class TrendQuestion(Base):
    __tablename__ = "trend_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    time_window: Mapped[str] = mapped_column(String(50), nullable=False) # daily / weekly / monthly
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
