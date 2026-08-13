"""Fixed-window rate limiter backed by MongoDB (RULE API-016)."""

from datetime import datetime, timedelta, timezone

from fastapi import Request

from app.core import db as database
from app.core.errors import AppError

# implementation/01_AUTHENTICATION.md RATE_LIMITS
LIMITS = {
    "auth.login": (10, 60),
    "auth.register": (5, 3600),
    "auth.forgot_password": (5, 3600),
    "auth.verify_email": (10, 3600),
    "auth.refresh": (60, 3600),
    "auth.google": (10, 60),
    "auth.reset_password": (5, 3600),
    "workspace.invite": (30, 3600),
    # Shopify (Feature 2.1) — SEC-017 / API-016.
    "shopify.install": (30, 3600),
    "shopify.callback": (60, 3600),
    "shopify.disconnect": (30, 3600),
    # Shopify (Feature 2.2) — manual sync.
    "shopify.sync": (10, 3600),
    # Shopify (Feature 2.3) — webhooks and incremental sync.
    "shopify.webhook": (1000, 3600),
    "shopify.webhook.test": (30, 3600),
    "shopify.sync.incremental": (10, 3600),
    # Razorpay (Milestone 3).
    "razorpay.connect": (30, 3600),
    "razorpay.disconnect": (30, 3600),
    "razorpay.sync": (10, 3600),
    "razorpay.webhook": (1000, 3600),
    # Reconciliation (Milestone 4).
    "reconciliation.run": (10, 3600),
    # Dashboard (Milestone 5).
    "dashboard.read": (60, 3600),
}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce(bucket: str, request: Request, subject: str | None = None) -> None:
    limit, window_seconds = LIMITS[bucket]
    now = datetime.now(timezone.utc)
    window_start = now.replace(microsecond=0) - timedelta(
        seconds=int(now.timestamp()) % window_seconds
    )
    key = f"{bucket}:{subject or client_ip(request)}:{int(window_start.timestamp())}"

    doc = await database.db[database.RATE_LIMIT].find_one_and_update(
        {"key": key},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"expires_at": window_start + timedelta(seconds=window_seconds * 2)},
        },
        upsert=True,
        return_document=True,
    )
    if doc and doc.get("count", 0) > limit:
        raise AppError("RATE_LIMIT-001")
