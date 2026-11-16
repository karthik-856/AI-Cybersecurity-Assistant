from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from backend.app.security.password import validate_password_complexity


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="VIEWER", pattern="^(VIEWER|SOC_ANALYST)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        is_valid, error = validate_password_complexity(v)
        if not is_valid:
            raise ValueError(error)
        return v


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str | None = None
    user: UserResponse | None = None
    requires_two_factor: bool = False
    otp_sent: bool = False
    challenge_token: str | None = None
    message: str | None = None


class TwoFactorRequest(BaseModel):
    action: str = Field(pattern="^(enable|disable)$")


class TwoFactorVerifyRequest(BaseModel):
    action: str = Field(pattern="^(enable|disable)$")
    otp: str = Field(min_length=6, max_length=6)


class TwoFactorLoginRequest(BaseModel):
    challenge_token: str = Field(min_length=1)
    otp: str = Field(min_length=6, max_length=6)


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr
    verification_required: bool = True


class MessageResponse(BaseModel):
    message: str


class EmailOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_reset_password_strength(cls, v: str) -> str:
        is_valid, error = validate_password_complexity(v)
        if not is_valid:
            raise ValueError(error)
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_change_password_strength(cls, v: str) -> str:
        is_valid, error = validate_password_complexity(v)
        if not is_valid:
            raise ValueError(error)
        return v