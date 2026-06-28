import uuid
import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case, String, DateTime, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    employee_code: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    db_role: Mapped[str] = mapped_column("role", String(50), nullable=False, default="employee", server_default="employee")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    action_requests: Mapped[list["ActionRequest"]] = relationship(
        "ActionRequest", back_populates="requester", cascade="all, delete-orphan"
    )

    @hybrid_property
    def role(self) -> str:
        if self.db_role == "admin":
            return "hr_admin"
        elif self.db_role == "hr":
            return "department_admin"
        return "employee"

    @role.setter
    def role(self, value: str):
        if value == "hr_admin" or value == "admin":
            self.db_role = "admin"
        elif value == "department_admin" or value == "hr":
            self.db_role = "hr"
        else:
            self.db_role = "employee"

    @role.expression
    def role(cls):
        return case(
            (cls.db_role == "admin", "hr_admin"),
            (cls.db_role == "hr", "department_admin"),
            else_="employee"
        )

    @property
    def role_access(self) -> str:
        if self.db_role == "admin":
            return "admin"
        elif self.db_role == "hr":
            return "department_admin"
        return "user"

    @role_access.setter
    def role_access(self, value: str):
        if value == "admin":
            self.db_role = "admin"
        elif value == "department_admin" or value == "hr_admin" or value == "hr":
            self.db_role = "hr"
        else:
            self.db_role = "employee"

    @property
    def department_id(self) -> str | None:
        return self.department

    @department_id.setter
    def department_id(self, value: str | None):
        self.department = value



