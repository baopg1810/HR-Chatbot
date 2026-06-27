import uuid
import datetime
from sqlalchemy import String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

class ActionRequest(Base):
    __tablename__ = "action_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_status: Mapped[str] = mapped_column(String(50), nullable=True, default="Chờ duyệt", server_default="'Chờ duyệt'::character varying")
    approver_email: Mapped[str] = mapped_column(String(255), nullable=True)
    generated_file: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    requester: Mapped["User"] = relationship("User", back_populates="action_requests")
