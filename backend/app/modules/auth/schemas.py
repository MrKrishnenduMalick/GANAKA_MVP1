"""Auth request / response DTOs (RULE API-004: entities are never returned)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    workspace_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1, max_length=128)


class MessageResponse(BaseModel):
    message: str


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    plan: str
    role: str | None = None
    is_owner: bool = False


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    profile_image_url: str | None = None
    status: str
    email_verified: bool
    last_login_at: datetime | None = None


class SessionSummary(BaseModel):
    id: str
    device: str | None = None
    browser: str | None = None
    ip: str | None = None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    current: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    user: UserProfile
    workspace: WorkspaceSummary | None = None
    permissions: list[str] = Field(default_factory=list)


class MeResponse(BaseModel):
    user: UserProfile
    workspace: WorkspaceSummary | None = None
    workspaces: list[WorkspaceSummary] = Field(default_factory=list)
    role: str | None = None
    permissions: list[str] = Field(default_factory=list)
    session_id: str
