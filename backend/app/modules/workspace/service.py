"""Workspace, membership, invitation and ownership business logic."""

import re
from datetime import timedelta

from fastapi import Request

from app.core import audit
from app.core import db as database
from app.core.config import settings
from app.core.deps import AuthContext, resolve_permissions
from app.core.errors import AppError
from app.core.models import new_id, utc_now
from app.core.pagination import PageRequest, page_response
from app.core.security import generate_opaque_token, hash_token
from app.services import email as email_service

MEMBER_SORT_FIELDS = {"created_at", "email", "full_name", "status"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


async def _unique_slug(name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 1
    while await database.db[database.WORKSPACE].find_one({"slug": slug}):
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


async def ensure_system_roles(workspace_id: str) -> None:
    """Idempotently create the five default roles for a workspace."""
    for name, permissions in database.SYSTEM_ROLE_PERMISSIONS.items():
        await database.db[database.ROLE].update_one(
            {"workspace_id": workspace_id, "name": name},
            {
                "$set": {"permissions": permissions, "is_system": True, "updated_at": utc_now()},
                "$setOnInsert": {
                    "_id": new_id(),
                    "description": f"Default {name.title()} role",
                    "created_at": utc_now(),
                    "deleted_at": None,
                },
            },
            upsert=True,
        )


async def create_workspace(*, owner: dict, name: str, request: Request | None = None, plan: str = "FREE") -> dict:
    now = utc_now()
    workspace = {
        "_id": new_id(),
        "name": name,
        "slug": await _unique_slug(name),
        "status": "ACTIVE",
        "owner_id": owner["_id"],
        "plan": plan,
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.WORKSPACE].insert_one(workspace)
    await ensure_system_roles(workspace["_id"])
    await database.db[database.WORKSPACE_MEMBER].insert_one(
        {
            "_id": new_id(),
            "workspace_id": workspace["_id"],
            "user_id": owner["_id"],
            "email": owner["email"],
            "full_name": owner.get("full_name", ""),
            "roles": ["OWNER"],
            "status": "ACTIVE",
            "invited_by": None,
            "joined_at": now,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    await database.db[database.WORKSPACE_SETTINGS].insert_one(
        {
            "_id": new_id(),
            "workspace_id": workspace["_id"],
            "company_name": name,
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "logo_url": None,
            "theme": "SYSTEM",
            "language": "en",
            "notification_settings": {"email_enabled": True},
            "security_settings": {"enforce_session_limit": True},
            "reconciliation_amount_tolerance": 0.00,
            "settlement_match_window_days": 15,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    await audit.record(
        action="WORKSPACE_CREATED",
        actor_user_id=owner["_id"],
        workspace_id=workspace["_id"],
        resource_type="WORKSPACE",
        resource_id=workspace["_id"],
        request=request,
        metadata={"name": name},
    )
    return workspace


def workspace_dto(workspace: dict, *, role: str | None = None, is_owner: bool = False) -> dict:
    return {
        "id": workspace["_id"],
        "name": workspace["name"],
        "slug": workspace["slug"],
        "status": workspace["status"],
        "plan": workspace["plan"],
        "role": role,
        "is_owner": is_owner,
    }


async def list_workspaces_for_user(user_id: str) -> list[dict]:
    memberships = database.db[database.WORKSPACE_MEMBER].find(
        {"user_id": user_id, "status": "ACTIVE", "deleted_at": None}
    )
    results: list[dict] = []
    async for member in memberships:
        workspace = await database.db[database.WORKSPACE].find_one(
            {"_id": member["workspace_id"], "deleted_at": None}
        )
        if not workspace:
            continue
        roles = member.get("roles", [])
        results.append(
            workspace_dto(
                workspace,
                role=roles[0] if roles else None,
                is_owner=workspace["owner_id"] == user_id,
            )
        )
    return sorted(results, key=lambda item: item["name"].lower())


async def get_workspace_scoped(context: AuthContext, workspace_id: str) -> dict:
    """Any lookup by path id must resolve inside the token's workspace."""
    if workspace_id != context.workspace_id:
        raise AppError("WORKSPACE-007")
    workspace = await database.db[database.WORKSPACE].find_one({"_id": workspace_id, "deleted_at": None})
    if not workspace:
        raise AppError("WORKSPACE-001")
    return workspace


async def update_workspace(context: AuthContext, workspace_id: str, payload: dict, request: Request) -> dict:
    workspace = await get_workspace_scoped(context, workspace_id)
    updates = {key: value for key, value in payload.items() if value is not None}
    if "status" in updates and not context.is_owner:
        raise AppError("WORKSPACE-006")
    if "name" in updates:
        updates["slug"] = await _unique_slug(updates["name"]) if updates["name"] != workspace["name"] else workspace["slug"]
    if not updates:
        return workspace
    updates["updated_at"] = utc_now()
    await database.db[database.WORKSPACE].update_one({"_id": workspace_id}, {"$set": updates})
    action = "WORKSPACE_SUSPENDED" if updates.get("status") == "SUSPENDED" else "WORKSPACE_UPDATED"
    await audit.record(
        action=action,
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="WORKSPACE",
        resource_id=workspace_id,
        request=request,
        metadata={"fields": sorted(updates.keys())},
    )
    return await database.db[database.WORKSPACE].find_one({"_id": workspace_id})


async def delete_workspace(context: AuthContext, workspace_id: str, request: Request) -> None:
    await get_workspace_scoped(context, workspace_id)
    now = utc_now()
    await database.db[database.WORKSPACE].update_one(
        {"_id": workspace_id}, {"$set": {"status": "DELETED", "deleted_at": now, "updated_at": now}}
    )
    await database.db[database.SESSION].update_many(
        {"workspace_id": workspace_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_reason": "WORKSPACE_DELETED", "updated_at": now}},
    )
    await audit.record(
        action="WORKSPACE_DELETED",
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="WORKSPACE",
        resource_id=workspace_id,
        request=request,
    )


async def get_settings(context: AuthContext, workspace_id: str) -> dict:
    await get_workspace_scoped(context, workspace_id)
    doc = await database.db[database.WORKSPACE_SETTINGS].find_one({"workspace_id": workspace_id})
    if not doc:
        raise AppError("WORKSPACE-001")
    return doc


async def update_settings(context: AuthContext, workspace_id: str, payload: dict, request: Request) -> dict:
    await get_settings(context, workspace_id)
    updates = {key: value for key, value in payload.items() if value is not None}
    if not updates:
        return await get_settings(context, workspace_id)
    updates["updated_at"] = utc_now()
    await database.db[database.WORKSPACE_SETTINGS].update_one({"workspace_id": workspace_id}, {"$set": updates})
    await audit.record(
        action="WORKSPACE_UPDATED",
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="WORKSPACE_SETTINGS",
        resource_id=workspace_id,
        request=request,
        metadata={"fields": sorted(updates.keys())},
    )
    return await get_settings(context, workspace_id)


def member_dto(member: dict, *, owner_id: str) -> dict:
    return {
        "id": member["_id"],
        "user_id": member["user_id"],
        "email": member["email"],
        "full_name": member.get("full_name", ""),
        "roles": member.get("roles", []),
        "status": member["status"],
        "is_owner": member["user_id"] == owner_id,
        "joined_at": member.get("joined_at"),
        "created_at": member["created_at"],
    }


async def list_members(context: AuthContext, page_request: PageRequest, status: str | None) -> dict:
    workspace = await get_workspace_scoped(context, context.workspace_id)
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if status:
        query["status"] = status
    total = await database.db[database.WORKSPACE_MEMBER].count_documents(query)
    cursor = (
        database.db[database.WORKSPACE_MEMBER]
        .find(query)
        .sort(page_request.sort_spec(MEMBER_SORT_FIELDS))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = [member_dto(doc, owner_id=workspace["owner_id"]) async for doc in cursor]
    return page_response(items, total, page_request)


async def _assert_role_exists(workspace_id: str, role_name: str) -> None:
    role = await database.db[database.ROLE].find_one(
        {"workspace_id": workspace_id, "name": role_name, "deleted_at": None}
    )
    if not role:
        raise AppError("WORKSPACE-008")


async def invite_member(context: AuthContext, email: str, role: str, request: Request) -> dict:
    workspace = await get_workspace_scoped(context, context.workspace_id)
    if role == "OWNER":
        raise AppError("WORKSPACE-006", "Ownership is granted through ownership transfer, not invitations.")
    await _assert_role_exists(context.workspace_id, role)

    email = email.lower()
    existing_member = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"workspace_id": context.workspace_id, "email": email, "status": {"$ne": "REMOVED"}, "deleted_at": None}
    )
    if existing_member:
        raise AppError("WORKSPACE-003")

    now = utc_now()
    raw_token = generate_opaque_token()
    invitation = {
        "_id": new_id(),
        "workspace_id": context.workspace_id,
        "email": email,
        "role": role,
        "token_hash": hash_token(raw_token),
        "status": "PENDING",
        "invited_by": context.user_id,
        "expires_at": now + timedelta(days=settings.INVITATION_TTL_DAYS),
        "accepted_at": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.WORKSPACE_INVITATION].insert_one(invitation)
    await email_service.send(
        "WORKSPACE_INVITATION",
        email,
        inviter=context.full_name or context.email,
        workspace_name=workspace["name"],
        role=role,
        link=f"{settings.APP_BASE_URL}/invitations/accept?token={raw_token}",
        ttl_days=settings.INVITATION_TTL_DAYS,
    )
    await audit.record(
        action="MEMBER_INVITED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="WORKSPACE_INVITATION",
        resource_id=invitation["_id"],
        request=request,
        metadata={"email": email, "role": role},
    )
    return {
        "id": invitation["_id"],
        "email": email,
        "role": role,
        "status": "PENDING",
        "expires_at": invitation["expires_at"],
    }


async def accept_invitation(*, user: dict, raw_token: str, request: Request) -> dict:
    invitation = await database.db[database.WORKSPACE_INVITATION].find_one(
        {"token_hash": hash_token(raw_token), "status": "PENDING", "deleted_at": None}
    )
    if not invitation:
        raise AppError("WORKSPACE-004")

    now = utc_now()
    expires_at = invitation["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        await database.db[database.WORKSPACE_INVITATION].update_one(
            {"_id": invitation["_id"]}, {"$set": {"status": "EXPIRED", "updated_at": now}}
        )
        raise AppError("WORKSPACE-005")
    if invitation["email"] != user["email"].lower():
        raise AppError("WORKSPACE-004")

    workspace = await database.db[database.WORKSPACE].find_one(
        {"_id": invitation["workspace_id"], "deleted_at": None, "status": "ACTIVE"}
    )
    if not workspace:
        raise AppError("WORKSPACE-001")

    await database.db[database.WORKSPACE_MEMBER].update_one(
        {"workspace_id": invitation["workspace_id"], "user_id": user["_id"]},
        {
            "$set": {
                "email": user["email"].lower(),
                "full_name": user.get("full_name", ""),
                "roles": [invitation["role"]],
                "status": "ACTIVE",
                "invited_by": invitation["invited_by"],
                "joined_at": now,
                "updated_at": now,
                "deleted_at": None,
            },
            "$setOnInsert": {"_id": new_id(), "created_at": now},
        },
        upsert=True,
    )
    await database.db[database.WORKSPACE_INVITATION].update_one(
        {"_id": invitation["_id"]}, {"$set": {"status": "ACCEPTED", "accepted_at": now, "updated_at": now}}
    )
    await audit.record(
        action="MEMBER_JOINED",
        actor_user_id=user["_id"],
        workspace_id=invitation["workspace_id"],
        resource_type="WORKSPACE_MEMBER",
        resource_id=user["_id"],
        request=request,
        metadata={"role": invitation["role"]},
    )
    return workspace_dto(workspace, role=invitation["role"], is_owner=False)


async def update_member(context: AuthContext, member_id: str, roles: list[str], request: Request) -> dict:
    workspace = await get_workspace_scoped(context, context.workspace_id)
    member = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"_id": member_id, "deleted_at": None}
    )
    if not member:
        raise AppError("WORKSPACE-010")
    if member["workspace_id"] != context.workspace_id:
        raise AppError("WORKSPACE-007")
    if member["user_id"] == workspace["owner_id"]:
        raise AppError("WORKSPACE-006", "The workspace owner's role cannot be changed.")
    if "OWNER" in roles:
        raise AppError("WORKSPACE-006", "Ownership is granted through ownership transfer.")
    for role_name in roles:
        await _assert_role_exists(context.workspace_id, role_name)

    await database.db[database.WORKSPACE_MEMBER].update_one(
        {"_id": member_id}, {"$set": {"roles": roles, "updated_at": utc_now()}}
    )
    await audit.record(
        action="PERMISSION_GRANTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="WORKSPACE_MEMBER",
        resource_id=member_id,
        request=request,
        metadata={"roles": roles},
    )
    updated = await database.db[database.WORKSPACE_MEMBER].find_one({"_id": member_id})
    return member_dto(updated, owner_id=workspace["owner_id"])


async def remove_member(context: AuthContext, member_id: str, request: Request) -> None:
    workspace = await get_workspace_scoped(context, context.workspace_id)
    member = await database.db[database.WORKSPACE_MEMBER].find_one({"_id": member_id, "deleted_at": None})
    if not member:
        raise AppError("WORKSPACE-010")
    if member["workspace_id"] != context.workspace_id:
        raise AppError("WORKSPACE-007")
    if member["user_id"] == workspace["owner_id"]:
        raise AppError("WORKSPACE-006", "The workspace owner cannot be removed.")

    now = utc_now()
    await database.db[database.WORKSPACE_MEMBER].update_one(
        {"_id": member_id}, {"$set": {"status": "REMOVED", "roles": [], "updated_at": now}}
    )
    await database.db[database.SESSION].update_many(
        {"workspace_id": context.workspace_id, "user_id": member["user_id"], "revoked": False},
        {"$set": {"revoked": True, "revoked_reason": "MEMBER_REMOVED", "updated_at": now}},
    )
    await audit.record(
        action="MEMBER_REMOVED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="WORKSPACE_MEMBER",
        resource_id=member_id,
        request=request,
        metadata={"email": member["email"]},
    )


async def transfer_ownership(context: AuthContext, workspace_id: str, new_owner_user_id: str, request: Request) -> dict:
    workspace = await get_workspace_scoped(context, workspace_id)
    if not context.is_owner:
        raise AppError("WORKSPACE-006")
    target = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"workspace_id": workspace_id, "user_id": new_owner_user_id, "status": "ACTIVE", "deleted_at": None}
    )
    if not target:
        raise AppError("WORKSPACE-010")

    now = utc_now()
    await database.db[database.WORKSPACE].update_one(
        {"_id": workspace_id}, {"$set": {"owner_id": new_owner_user_id, "updated_at": now}}
    )
    await database.db[database.WORKSPACE_MEMBER].update_one(
        {"_id": target["_id"]}, {"$set": {"roles": ["OWNER"], "updated_at": now}}
    )
    await database.db[database.WORKSPACE_MEMBER].update_one(
        {"workspace_id": workspace_id, "user_id": context.user_id},
        {"$set": {"roles": ["ADMIN"], "updated_at": now}},
    )
    await audit.record(
        action="OWNERSHIP_TRANSFERRED",
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="WORKSPACE",
        resource_id=workspace_id,
        request=request,
        metadata={"previous_owner": context.user_id, "new_owner": new_owner_user_id},
    )
    updated = await database.db[database.WORKSPACE].find_one({"_id": workspace_id})
    return workspace_dto(updated, role="ADMIN", is_owner=False)


async def permissions_for_member(workspace_id: str, user_id: str) -> list[str]:
    member = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"workspace_id": workspace_id, "user_id": user_id, "status": "ACTIVE", "deleted_at": None}
    )
    if not member:
        raise AppError("WORKSPACE-002")
    return await resolve_permissions(workspace_id, member.get("roles", []))
