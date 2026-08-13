"""Authentication, session and identity business logic."""

import logging
from datetime import timedelta

import httpx
from fastapi import Request

from app.core import audit
from app.core import db as database
from app.core.config import settings
from app.core.deps import AuthContext, resolve_permissions
from app.core.errors import AppError
from app.core.models import new_id, utc_now
from app.core.rate_limit import client_ip
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_policy,
    verify_password,
)
from app.modules.workspace import service as workspace_service
from app.services import email as email_service

logger = logging.getLogger("ganaka.auth")

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Constant-time-ish decoy so a non-existent email costs the same as a wrong password.
_DECOY_HASH = hash_password("Ganaka-Decoy-Password-1!")

GENERIC_REGISTER_MESSAGE = "Check your email to verify your account."
GENERIC_FORGOT_MESSAGE = "If an account exists for that email, a password reset link has been sent."


def user_profile_dto(user: dict) -> dict:
    return {
        "id": user["_id"],
        "email": user["email"],
        "full_name": user.get("full_name", ""),
        "phone": user.get("phone"),
        "profile_image_url": user.get("profile_image_url"),
        "status": user["status"],
        "email_verified": user.get("email_verified_at") is not None,
        "last_login_at": user.get("last_login_at"),
    }


def session_dto(session: dict, current_session_id: str) -> dict:
    return {
        "id": session["_id"],
        "device": session.get("device"),
        "browser": session.get("browser"),
        "ip": session.get("ip"),
        "created_at": session["created_at"],
        "last_activity": session.get("last_activity") or session["created_at"],
        "expires_at": session["expires_at"],
        "current": session["_id"] == current_session_id,
    }


def _parse_user_agent(request: Request) -> tuple[str, str]:
    agent = request.headers.get("user-agent", "")
    device = "Mobile" if any(token in agent for token in ("Mobile", "Android", "iPhone")) else "Desktop"
    for browser in ("Edg", "Chrome", "Firefox", "Safari"):
        if browser in agent:
            return device, ("Edge" if browser == "Edg" else browser)
    return device, "Unknown"


async def _enforce_session_limit(user_id: str) -> None:
    query = {"user_id": user_id, "revoked": False}
    active = await database.db[database.SESSION].count_documents(query)
    overflow = active - (settings.MAX_ACTIVE_SESSIONS - 1)
    if overflow <= 0:
        return
    cursor = database.db[database.SESSION].find(query).sort("last_activity", 1).limit(overflow)
    async for stale in cursor:
        await database.db[database.SESSION].update_one(
            {"_id": stale["_id"]},
            {"$set": {"revoked": True, "revoked_reason": "SESSION_LIMIT", "updated_at": utc_now()}},
        )


async def issue_session_tokens(
    *, user: dict, workspace_id: str | None, request: Request, reuse_session_id: str | None = None
) -> tuple[dict, str]:
    """Create (or rotate) a session and mint an access + refresh token pair."""
    now = utc_now()
    raw_refresh = generate_opaque_token()
    device, browser = _parse_user_agent(request)

    if reuse_session_id:
        session_id = reuse_session_id
        await database.db[database.SESSION].update_one(
            {"_id": session_id},
            {
                "$set": {
                    "refresh_token_hash": hash_token(raw_refresh),
                    "workspace_id": workspace_id,
                    "last_activity": now,
                    "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
                    "updated_at": now,
                }
            },
        )
    else:
        await _enforce_session_limit(user["_id"])
        session_id = new_id()
        await database.db[database.SESSION].insert_one(
            {
                "_id": session_id,
                "user_id": user["_id"],
                "workspace_id": workspace_id,
                "refresh_token_hash": hash_token(raw_refresh),
                "device": device,
                "browser": browser,
                "ip": client_ip(request),
                "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
                "last_activity": now,
                "revoked": False,
                "revoked_reason": None,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )
        await audit.record(
            action="SESSION_CREATED",
            actor_user_id=user["_id"],
            workspace_id=workspace_id,
            resource_type="SESSION",
            resource_id=session_id,
            request=request,
        )

    role, permissions, workspace_summary = None, [], None
    if workspace_id:
        member = await database.db[database.WORKSPACE_MEMBER].find_one(
            {"workspace_id": workspace_id, "user_id": user["_id"], "status": "ACTIVE", "deleted_at": None}
        )
        if not member:
            raise AppError("WORKSPACE-002")
        role_names = member.get("roles", [])
        role = role_names[0] if role_names else None
        permissions = await resolve_permissions(workspace_id, role_names)
        workspace = await database.db[database.WORKSPACE].find_one({"_id": workspace_id, "deleted_at": None})
        if not workspace:
            raise AppError("WORKSPACE-001")
        workspace_summary = workspace_service.workspace_dto(
            workspace, role=role, is_owner=workspace["owner_id"] == user["_id"]
        )

    access_token, expires_at = create_access_token(
        user_id=user["_id"],
        workspace_id=workspace_id,
        role=role,
        permissions=permissions,
        session_id=session_id,
    )
    payload = {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "Bearer",
        "expires_at": expires_at,
        "user": user_profile_dto(user),
        "workspace": workspace_summary,
        "permissions": permissions,
    }
    return payload, raw_refresh


async def register(payload, request: Request) -> dict:
    validate_password_policy(payload.password)
    email = payload.email.lower()
    password_hash = hash_password(payload.password)

    existing = await database.db[database.USER].find_one({"email": email})
    if existing:
        # REGISTER_ENUMERATION_PROTECTION: identical response, side-channel email instead.
        await email_service.send(
            "REGISTER_COLLISION",
            email,
            link=f"{settings.APP_BASE_URL}/forgot-password",
        )
        await audit.record(
            action="USER_REGISTERED",
            status="REJECTED_DUPLICATE_EMAIL",
            workspace_id=None,
            resource_type="USER",
            resource_id=existing["_id"],
            request=request,
        )
        return {"message": GENERIC_REGISTER_MESSAGE}

    now = utc_now()
    user = {
        "_id": new_id(),
        "email": email,
        "full_name": payload.full_name,
        "phone": None,
        "profile_image_url": None,
        "password_hash": password_hash,
        "status": "EMAIL_PENDING",
        "email_verified_at": None,
        "failed_login_count": 0,
        "locked_until": None,
        "last_login_at": None,
        "default_workspace_id": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.USER].insert_one(user)

    workspace = await workspace_service.create_workspace(
        owner=user, name=payload.workspace_name or f"{payload.full_name}'s Workspace", request=request
    )
    await database.db[database.USER].update_one(
        {"_id": user["_id"]}, {"$set": {"default_workspace_id": workspace["_id"], "updated_at": utc_now()}}
    )

    raw_token = generate_opaque_token()
    await database.db[database.EMAIL_VERIFICATION_TOKEN].insert_one(
        {
            "_id": new_id(),
            "user_id": user["_id"],
            "token_hash": hash_token(raw_token),
            "expires_at": now + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
            "used_at": None,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    await email_service.send(
        "VERIFY_EMAIL",
        email,
        link=f"{settings.APP_BASE_URL}/verify-email?token={raw_token}",
        ttl_hours=settings.EMAIL_VERIFICATION_TTL_HOURS,
    )
    await audit.record(
        action="USER_REGISTERED",
        actor_user_id=user["_id"],
        workspace_id=workspace["_id"],
        resource_type="USER",
        resource_id=user["_id"],
        request=request,
    )
    return {"message": GENERIC_REGISTER_MESSAGE}


async def verify_email(raw_token: str, request: Request) -> dict:
    token_doc = await database.db[database.EMAIL_VERIFICATION_TOKEN].find_one(
        {"token_hash": hash_token(raw_token), "used_at": None}
    )
    if not token_doc:
        raise AppError("AUTH-009")

    now = utc_now()
    expires_at = token_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise AppError("AUTH-009")

    await database.db[database.EMAIL_VERIFICATION_TOKEN].update_one(
        {"_id": token_doc["_id"]}, {"$set": {"used_at": now, "updated_at": now}}
    )
    await database.db[database.USER].update_one(
        {"_id": token_doc["user_id"]},
        {"$set": {"status": "ACTIVE", "email_verified_at": now, "updated_at": now}},
    )
    await audit.record(
        action="EMAIL_VERIFIED",
        actor_user_id=token_doc["user_id"],
        resource_type="USER",
        resource_id=token_doc["user_id"],
        request=request,
    )
    return {"message": "Email verified. You can now sign in."}


async def _register_failed_login(user: dict, request: Request) -> None:
    now = utc_now()
    failures = user.get("failed_login_count", 0) + 1
    updates = {"failed_login_count": failures, "updated_at": now}
    if failures >= settings.MAX_FAILED_LOGINS:
        updates.update(
            {
                "status": "LOCKED",
                "locked_until": now + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES),
                "failed_login_count": 0,
            }
        )
    await database.db[database.USER].update_one({"_id": user["_id"]}, {"$set": updates})

    if "locked_until" in updates:
        await email_service.send(
            "ACCOUNT_LOCKED",
            user["email"],
            lock_minutes=settings.ACCOUNT_LOCK_MINUTES,
            attempts=settings.MAX_FAILED_LOGINS,
        )
        await audit.record(
            action="ACCOUNT_LOCKED",
            status="FAILURE",
            actor_user_id=user["_id"],
            resource_type="USER",
            resource_id=user["_id"],
            request=request,
        )
    await audit.record(
        action="LOGIN_FAILED",
        status="FAILURE",
        actor_user_id=user["_id"],
        resource_type="USER",
        resource_id=user["_id"],
        request=request,
    )


async def login(payload, request: Request) -> tuple[dict, str]:
    email = payload.email.lower()
    user = await database.db[database.USER].find_one({"email": email, "deleted_at": None})
    if not user:
        verify_password(payload.password, _DECOY_HASH)
        await audit.record(
            action="LOGIN_FAILED", status="FAILURE", request=request, metadata={"reason": "UNKNOWN_EMAIL"}
        )
        raise AppError("AUTH-001")

    now = utc_now()
    locked_until = user.get("locked_until")
    if locked_until:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=now.tzinfo)
        if locked_until > now:
            raise AppError("AUTH-005")
        await database.db[database.USER].update_one(
            {"_id": user["_id"]},
            {"$set": {"locked_until": None, "failed_login_count": 0, "status": "ACTIVE", "updated_at": now}},
        )
        user["status"] = "ACTIVE"
        await audit.record(
            action="ACCOUNT_UNLOCKED", actor_user_id=user["_id"], resource_type="USER",
            resource_id=user["_id"], request=request,
        )

    if user["status"] in {"DISABLED", "DELETED"}:
        raise AppError("AUTH-011")

    if not verify_password(payload.password, user.get("password_hash") or ""):
        await _register_failed_login(user, request)
        raise AppError("AUTH-001")

    if user.get("email_verified_at") is None:
        raise AppError("AUTH-004")

    await database.db[database.USER].update_one(
        {"_id": user["_id"]},
        {"$set": {"failed_login_count": 0, "locked_until": None, "last_login_at": now, "updated_at": now}},
    )
    user["last_login_at"] = now

    workspace_id = user.get("default_workspace_id")
    if workspace_id:
        member = await database.db[database.WORKSPACE_MEMBER].find_one(
            {"workspace_id": workspace_id, "user_id": user["_id"], "status": "ACTIVE", "deleted_at": None}
        )
        if not member:
            workspace_id = None
    if not workspace_id:
        memberships = await workspace_service.list_workspaces_for_user(user["_id"])
        workspace_id = memberships[0]["id"] if memberships else None

    payload_out, raw_refresh = await issue_session_tokens(
        user=user, workspace_id=workspace_id, request=request
    )
    await audit.record(
        action="LOGIN_SUCCESS",
        actor_user_id=user["_id"],
        workspace_id=workspace_id,
        resource_type="USER",
        resource_id=user["_id"],
        request=request,
    )
    return payload_out, raw_refresh


async def google_login(id_token: str, request: Request) -> tuple[dict, str]:
    if not settings.google_configured:
        raise AppError(
            "EXTERNAL-001", "Google sign-in is not configured on this deployment."
        )
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            response = await http_client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.HTTPError:
        raise AppError("EXTERNAL-001")
    if response.status_code != 200:
        raise AppError("AUTH-003")

    claims = response.json()
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise AppError("AUTH-003")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AppError("AUTH-003")
    if str(claims.get("email_verified", "")).lower() not in {"true", "1"}:
        raise AppError("AUTH-003")

    email = (claims.get("email") or "").lower()
    provider_user_id = claims.get("sub")
    if not email or not provider_user_id:
        raise AppError("AUTH-003")

    now = utc_now()
    linked = await database.db[database.OAUTH_ACCOUNT].find_one(
        {"provider": "GOOGLE", "provider_user_id": provider_user_id}
    )
    user = None
    if linked:
        user = await database.db[database.USER].find_one({"_id": linked["user_id"], "deleted_at": None})

    if user is None:
        existing = await database.db[database.USER].find_one({"email": email, "deleted_at": None})
        if existing:
            # ACCOUNT_LINKING_CHECK case 2: never silently adopt a password account.
            await email_service.send(
                "GOOGLE_LINKING_REQUIRED", email, link=f"{settings.APP_BASE_URL}/forgot-password"
            )
            await audit.record(
                action="LOGIN_FAILED",
                status="FAILURE",
                actor_user_id=existing["_id"],
                resource_type="USER",
                resource_id=existing["_id"],
                request=request,
                metadata={"reason": "ACCOUNT_LINKING_REQUIRED"},
            )
            raise AppError("AUTH-008")

        user = {
            "_id": new_id(),
            "email": email,
            "full_name": claims.get("name") or email.split("@")[0],
            "phone": None,
            "profile_image_url": claims.get("picture"),
            "password_hash": None,
            "status": "ACTIVE",
            "email_verified_at": now,
            "failed_login_count": 0,
            "locked_until": None,
            "last_login_at": now,
            "default_workspace_id": None,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        await database.db[database.USER].insert_one(user)
        workspace = await workspace_service.create_workspace(
            owner=user, name=f"{user['full_name']}'s Workspace", request=request
        )
        await database.db[database.USER].update_one(
            {"_id": user["_id"]}, {"$set": {"default_workspace_id": workspace["_id"]}}
        )
        user["default_workspace_id"] = workspace["_id"]
        await database.db[database.OAUTH_ACCOUNT].insert_one(
            {
                "_id": new_id(),
                "user_id": user["_id"],
                "provider": "GOOGLE",
                "provider_user_id": provider_user_id,
                "email": email,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )
        await audit.record(
            action="USER_REGISTERED",
            actor_user_id=user["_id"],
            workspace_id=workspace["_id"],
            resource_type="USER",
            resource_id=user["_id"],
            request=request,
            metadata={"provider": "GOOGLE"},
        )

    if user["status"] in {"DISABLED", "DELETED"}:
        raise AppError("AUTH-011")

    workspace_id = user.get("default_workspace_id")
    if not workspace_id:
        memberships = await workspace_service.list_workspaces_for_user(user["_id"])
        workspace_id = memberships[0]["id"] if memberships else None

    payload_out, raw_refresh = await issue_session_tokens(
        user=user, workspace_id=workspace_id, request=request
    )
    await audit.record(
        action="GOOGLE_LOGIN_SUCCESS",
        actor_user_id=user["_id"],
        workspace_id=workspace_id,
        resource_type="USER",
        resource_id=user["_id"],
        request=request,
    )
    return payload_out, raw_refresh


async def refresh(raw_refresh: str, request: Request) -> tuple[dict, str]:
    session = await database.db[database.SESSION].find_one(
        {"refresh_token_hash": hash_token(raw_refresh), "revoked": False}
    )
    if not session:
        raise AppError("AUTH-003")

    now = utc_now()
    expires_at = session["expires_at"]
    last_activity = session.get("last_activity") or session["created_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=now.tzinfo)
    if expires_at <= now or (now - last_activity) > timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES):
        await database.db[database.SESSION].update_one(
            {"_id": session["_id"]},
            {"$set": {"revoked": True, "revoked_reason": "EXPIRED", "updated_at": now}},
        )
        raise AppError("AUTH-006")

    user = await database.db[database.USER].find_one({"_id": session["user_id"], "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    if user["status"] in {"DISABLED", "DELETED"}:
        raise AppError("AUTH-011")

    payload_out, new_refresh = await issue_session_tokens(
        user=user,
        workspace_id=session.get("workspace_id"),
        request=request,
        reuse_session_id=session["_id"],
    )
    await audit.record(
        action="SESSION_REFRESHED",
        actor_user_id=user["_id"],
        workspace_id=session.get("workspace_id"),
        resource_type="SESSION",
        resource_id=session["_id"],
        request=request,
    )
    return payload_out, new_refresh


async def logout(context: AuthContext, request: Request) -> dict:
    await database.db[database.SESSION].update_one(
        {"_id": context.session_id},
        {"$set": {"revoked": True, "revoked_reason": "LOGOUT", "updated_at": utc_now()}},
    )
    await audit.record(
        action="SESSION_REVOKED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SESSION",
        resource_id=context.session_id,
        request=request,
    )
    return {"message": "Signed out."}


async def logout_all(context: AuthContext, request: Request) -> dict:
    result = await database.db[database.SESSION].update_many(
        {"user_id": context.user_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_reason": "LOGOUT_ALL", "updated_at": utc_now()}},
    )
    await audit.record(
        action="SESSION_REVOKED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SESSION",
        request=request,
        metadata={"revoked_count": result.modified_count, "scope": "ALL"},
    )
    return {"message": "Signed out of all sessions."}


async def revoke_session(context: AuthContext, session_id: str, request: Request) -> dict:
    session = await database.db[database.SESSION].find_one({"_id": session_id})
    if not session or session["user_id"] != context.user_id:
        raise AppError("AUTHZ-001")
    await database.db[database.SESSION].update_one(
        {"_id": session_id},
        {"$set": {"revoked": True, "revoked_reason": "USER_REVOKED", "updated_at": utc_now()}},
    )
    await audit.record(
        action="SESSION_REVOKED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SESSION",
        resource_id=session_id,
        request=request,
    )
    return {"message": "Session revoked."}


async def list_sessions(context: AuthContext) -> list[dict]:
    cursor = database.db[database.SESSION].find(
        {"user_id": context.user_id, "revoked": False}
    ).sort("last_activity", -1)
    return [session_dto(doc, context.session_id) async for doc in cursor]


async def forgot_password(email: str, request: Request) -> dict:
    email = email.lower()
    user = await database.db[database.USER].find_one({"email": email, "deleted_at": None})
    if user:
        now = utc_now()
        raw_token = generate_opaque_token()
        await database.db[database.PASSWORD_RESET_TOKEN].insert_one(
            {
                "_id": new_id(),
                "user_id": user["_id"],
                "token_hash": hash_token(raw_token),
                "expires_at": now + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
                "used_at": None,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )
        await email_service.send(
            "PASSWORD_RESET",
            email,
            link=f"{settings.APP_BASE_URL}/reset-password?token={raw_token}",
            ttl_minutes=settings.PASSWORD_RESET_TTL_MINUTES,
        )
        await audit.record(
            action="PASSWORD_RESET_REQUESTED",
            actor_user_id=user["_id"],
            resource_type="USER",
            resource_id=user["_id"],
            request=request,
        )
    return {"message": GENERIC_FORGOT_MESSAGE}


async def reset_password(raw_token: str, new_password: str, request: Request) -> dict:
    validate_password_policy(new_password)
    token_doc = await database.db[database.PASSWORD_RESET_TOKEN].find_one(
        {"token_hash": hash_token(raw_token), "used_at": None}
    )
    if not token_doc:
        raise AppError("AUTH-009")

    now = utc_now()
    expires_at = token_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise AppError("AUTH-009")

    user = await database.db[database.USER].find_one({"_id": token_doc["user_id"], "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")

    await database.db[database.PASSWORD_RESET_TOKEN].update_one(
        {"_id": token_doc["_id"]}, {"$set": {"used_at": now, "updated_at": now}}
    )
    await database.db[database.USER].update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "failed_login_count": 0,
                "locked_until": None,
                # A verified reset link also proves ownership of the mailbox.
                "status": "ACTIVE",
                "email_verified_at": user.get("email_verified_at") or now,
                "updated_at": now,
            }
        },
    )
    await database.db[database.SESSION].update_many(
        {"user_id": user["_id"], "revoked": False},
        {"$set": {"revoked": True, "revoked_reason": "PASSWORD_CHANGED", "updated_at": now}},
    )
    await email_service.send("PASSWORD_CHANGED", user["email"])
    await audit.record(
        action="PASSWORD_CHANGED",
        actor_user_id=user["_id"],
        resource_type="USER",
        resource_id=user["_id"],
        request=request,
    )
    return {"message": "Password updated. Please sign in again."}


async def me(context: AuthContext) -> dict:
    user = await database.db[database.USER].find_one({"_id": context.user_id, "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    workspaces = await workspace_service.list_workspaces_for_user(context.user_id)
    current = next((item for item in workspaces if item["id"] == context.workspace_id), None)
    return {
        "user": user_profile_dto(user),
        "workspace": current,
        "workspaces": workspaces,
        "role": context.role,
        "permissions": context.permissions,
        "session_id": context.session_id,
    }
