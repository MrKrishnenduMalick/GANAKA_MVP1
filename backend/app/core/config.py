import logging
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger("ganaka.config")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw not in (None, "") else default


def _resolve_cors_origins(app_base_url: str) -> list[str]:
    """ARCH-AUDIT-011 fix: the API always issues the refresh cookie with
    `allow_credentials=True`. A wildcard origin combined with credentialed
    requests lets any website read authenticated responses in a browser
    context, so `*` is never honored here. If CORS_ORIGINS is not set to an
    explicit, non-wildcard list, fail closed to APP_BASE_URL (the deployment's
    own declared origin) instead of guessing at production domains; if
    neither is configured, cross-origin credentialed requests are rejected.
    """
    raw = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]
    if raw and "*" not in raw:
        return raw
    if raw and "*" in raw:
        logger.warning(
            "CORS_ORIGINS=\"*\" is ignored because allow_credentials=True; "
            "falling back to APP_BASE_URL. Set an explicit origin list to silence this."
        )
    if app_base_url:
        return [app_base_url]
    logger.warning(
        "No usable CORS_ORIGINS or APP_BASE_URL configured; cross-origin "
        "credentialed requests will be rejected until one is set."
    )
    return []


class Settings:
    """Externalized configuration. Secrets come from the environment only."""

    API_PREFIX = "/api/v1"

    MONGO_URL = os.environ["MONGO_URL"]
    DB_NAME = os.environ["DB_NAME"]
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "")
    CORS_ORIGINS = _resolve_cors_origins(APP_BASE_URL)
    # ARCH-AUDIT-012 fix: test-only webhook replay endpoint is disabled unless
    # explicitly turned on for a non-production environment.
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")
    ENABLE_TEST_ENDPOINTS = os.environ.get("ENABLE_TEST_ENDPOINTS", "false").lower() == "true"

    JWT_SECRET = os.environ["JWT_SECRET"]
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_TTL_MINUTES = _int("ACCESS_TOKEN_TTL_MINUTES", 15)
    REFRESH_TOKEN_TTL_DAYS = _int("REFRESH_TOKEN_TTL_DAYS", 30)
    SESSION_IDLE_TIMEOUT_MINUTES = _int("SESSION_IDLE_TIMEOUT_MINUTES", 30)
    MAX_ACTIVE_SESSIONS = _int("MAX_ACTIVE_SESSIONS", 5)

    MAX_FAILED_LOGINS = _int("MAX_FAILED_LOGINS", 5)
    ACCOUNT_LOCK_MINUTES = _int("ACCOUNT_LOCK_MINUTES", 15)

    EMAIL_VERIFICATION_TTL_HOURS = _int("EMAIL_VERIFICATION_TTL_HOURS", 24)
    PASSWORD_RESET_TTL_MINUTES = _int("PASSWORD_RESET_TTL_MINUTES", 15)
    INVITATION_TTL_DAYS = _int("INVITATION_TTL_DAYS", 7)

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")

    MAX_CUSTOM_ROLES = _int("MAX_CUSTOM_ROLES", 50)
    MAX_PERMISSIONS_PER_ROLE = _int("MAX_PERMISSIONS_PER_ROLE", 200)

    # --- Shopify (Feature 2.1) ---
    SHOPIFY_API_KEY = os.environ.get("SHOPIFY_API_KEY") or os.environ.get("SHOPIFY_CLIENT_ID", "")
    SHOPIFY_API_SECRET = os.environ.get("SHOPIFY_API_SECRET") or os.environ.get("SHOPIFY_CLIENT_SECRET", "")
    SHOPIFY_SCOPES = os.environ.get("SHOPIFY_SCOPES", "")
    SHOPIFY_APP_URL = os.environ.get("SHOPIFY_APP_URL") or os.environ.get("APP_BASE_URL", "")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    SHOPIFY_OAUTH_STATE_TTL_MINUTES = _int("SHOPIFY_OAUTH_STATE_TTL_MINUTES", 15)

    # --- Razorpay (Milestone 3) ---
    # ARCH-AUDIT-001 fix: Razorpay is multi-tenant. Each workspace supplies and
    # stores its own encrypted key_id/key_secret/webhook_secret (see
    # RazorpayConnectRequest / connect_razorpay). No platform-wide Razorpay
    # credential is used to service tenant requests any more. RAZORPAY_SYNC_TTL_MINUTES
    # and ENCRYPTION_KEY remain deployment-level configuration.
    RAZORPAY_SYNC_TTL_MINUTES = _int("RAZORPAY_SYNC_TTL_MINUTES", 15)

    @property
    def email_transport_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_FROM)

    @property
    def google_configured(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID)

    @property
    def shopify_configured(self) -> bool:
        return bool(
            self.SHOPIFY_API_KEY
            and self.SHOPIFY_API_SECRET
            and self.SHOPIFY_SCOPES
            and self.SHOPIFY_APP_URL
            and self.ENCRYPTION_KEY
        )

    @property
    def razorpay_configured(self) -> bool:
        """Razorpay credentials are per-workspace now (ARCH-AUDIT-001); the
        deployment only needs a credential-encryption key to support it."""
        return bool(self.ENCRYPTION_KEY)


settings = Settings()
