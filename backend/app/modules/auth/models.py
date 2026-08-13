"""Auth / identity documents."""

from datetime import datetime

from pydantic import EmailStr, Field

from app.core.models import BaseDocument


class User(BaseDocument):
    email: EmailStr
    full_name: str
    phone: str | None = None
    profile_image_url: str | None = None
    password_hash: str | None = None
    status: str = "EMAIL_PENDING"  # REGISTERED|EMAIL_PENDING|ACTIVE|LOCKED|DISABLED|DELETED
    email_verified_at: datetime | None = None
    failed_login_count: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    default_workspace_id: str | None = None


class Session(BaseDocument):
    user_id: str
    workspace_id: str | None = None
    refresh_token_hash: str
    device: str | None = None
    browser: str | None = None
    ip: str | None = None
    expires_at: datetime
    last_activity: datetime
    revoked: bool = False
    revoked_reason: str | None = None


class OAuthAccount(BaseDocument):
    user_id: str
    provider: str = "GOOGLE"
    provider_user_id: str
    email: EmailStr


class VerificationToken(BaseDocument):
    """Backs both email_verification_token and password_reset_token."""

    user_id: str
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
