import uuid
from sqlalchemy import String, Text, Integer, JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visibility_roles: Mapped[list | dict] = mapped_column(JSON, nullable=False, server_default="[]")
    department_ids: Mapped[list | dict] = mapped_column(JSON, nullable=False, server_default="[]")
    embedding: Mapped[list | dict] = mapped_column(JSON, nullable=False, server_default="[]")
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, nullable=False, server_default="{}")

    document: Mapped["Document"] = relationship("Document")
