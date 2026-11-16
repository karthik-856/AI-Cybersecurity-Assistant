from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from backend.app.security.password import validate_password_complexity


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="SOC_ANALYST", pattern="^(VIEWER|SOC_ANALYST)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        is_valid, error = validate_password_complexity(v)
        if not is_valid:
            raise ValueError(error)
        return v


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    last_login_ip: str | None

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRoleRequest(BaseModel):
    role: str


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class LoginAuditResponse(BaseModel):
    id: int
    user_id: int | None
    username: str | None
    login_at: datetime
    ip_address: str | None
    success: bool
    user_agent: str | None