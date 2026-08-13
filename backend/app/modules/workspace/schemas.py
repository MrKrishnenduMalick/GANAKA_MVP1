"""Workspace / membership DTOs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ROLE_NAME_PATTERN = r"^[A-Z][A-Z0-9_]{1,31}$"


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class WorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: str | None = Field(default=None, pattern="^(ACTIVE|SUSPENDED|ARCHIVED)$")


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    plan: str
    timezone: str
    currency: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class WorkspaceSettingsResponse(BaseModel):
    workspace_id: str
    company_name: str | None = None
    timezone: str
    currency: str
    logo_url: str | None = None
    theme: str
    language: str
    notification_settings: dict = Field(default_factory=dict)
    security_settings: dict = Field(default_factory=dict)
    reconciliation_amount_tolerance: float
    settlement_match_window_days: int


class WorkspaceSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    logo_url: str | None = Field(default=None, max_length=500)
    theme: str | None = Field(default=None, pattern="^(LIGHT|DARK|SYSTEM)$")
    language: str | None = Field(default=None, min_length=2, max_length=5)
    notification_settings: dict | None = None
    security_settings: dict | None = None
    reconciliation_amount_tolerance: float | None = Field(default=None, ge=0, le=5)
    settlement_match_window_days: int | None = Field(default=None, ge=1, le=45)


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: EmailStr
    full_name: str
    roles: list[str]
    status: str
    is_owner: bool
    joined_at: datetime | None = None
    created_at: datetime


class MemberPage(BaseModel):
    items: list[MemberResponse]
    page: int
    size: int
    total: int
    total_pages: int


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    role: str = Field(pattern=ROLE_NAME_PATTERN)


class InvitationResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    status: str
    expires_at: datetime


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=10)


class MemberUpdateRequest(BaseModel):
    roles: list[str] = Field(min_length=1, max_length=5)


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: str = Field(min_length=1)
