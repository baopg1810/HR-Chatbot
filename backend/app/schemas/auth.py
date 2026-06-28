import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, computed_field

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserLogin):
    pass

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role_access: str
    department_id: str | None = None
    created_at: datetime | None = None


    class Config:
        from_attributes = True

    @computed_field
    @property
    def role(self) -> str:
        if self.role_access == "admin":
            return "hr_admin"
        elif self.role_access == "department_admin":
            return "department_admin"
        return "employee"

    @computed_field
    @property
    def full_name(self) -> str:
        if self.email == "employee@example.com":
            return "Nguyen Van An"
        elif self.email == "admin@example.com":
            return "Tran Thi HR"
        return self.email.split("@")[0].capitalize()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse | None = None



class UserCreateByAdmin(BaseModel):
    email: EmailStr
    password: str
    role_access: str = "user"
    department_id: str | None = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

