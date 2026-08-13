"""Append-only audit trail (RULE API-019). Audit rows are never updated."""

import logging

from fastapi import Request

from app.core import db as database
from app.core.models import new_id, utc_now
from app.core.rate_limit import client_ip

logger = logging.getLogger("ganaka.audit")

SENSITIVE_KEYS = {"password", "token", "refresh_token", "secret", "authorization"}


def _scrub(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    return {
        key: ("[redacted]" if key.lower() in SENSITIVE_KEYS else value)
        for key, value in metadata.items()
    }


async def record(
    *,
    action: str,
    status: str = "SUCCESS",
    actor_user_id: str | None = None,
    workspace_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
    metadata: dict | None = None,
) -> None:
    doc = {
        "_id": new_id(),
        "action": action,
        "status": status,
        "actor_user_id": actor_user_id,
        "workspace_id": workspace_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip": client_ip(request) if request else None,
        "user_agent": request.headers.get("user-agent") if request else None,
        "request_id": getattr(request.state, "request_id", None) if request else None,
        "metadata": _scrub(metadata),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    await database.db[database.AUDIT_LOG].insert_one(doc)
    logger.info(
        "audit action=%s status=%s workspace_id=%s actor=%s", action, status, workspace_id, actor_user_id
    )
