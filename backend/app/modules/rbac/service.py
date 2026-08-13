"""Role / permission business logic. Permissions are never hardcoded per role
at call sites: they are resolved from the workspace's role documents."""

from fastapi import Request

from app.core import audit
from app.core import db as database
from app.core.config import settings
from app.core.deps import AuthContext
from app.core.errors import AppError
from app.core.models import new_id, utc_now
from app.core.pagination import PageRequest, page_response

ROLE_SORT_FIELDS = {"created_at", "name"}
PERMISSION_SORT_FIELDS = {"code", "category"}
CUSTOM_ROLE_PLANS = {"PRO", "ENTERPRISE"}


def role_dto(role: dict) -> dict:
    return {
        "id": role["_id"],
        "name": role["name"],
        "description": role.get("description"),
        "permissions": role.get("permissions", []),
        "is_system": role.get("is_system", False),
        "created_at": role["created_at"],
        "updated_at": role["updated_at"],
    }


async def list_roles(context: AuthContext, page_request: PageRequest) -> dict:
    query = {"workspace_id": context.workspace_id, "deleted_at": None}
    total = await database.db[database.ROLE].count_documents(query)
    cursor = (
        database.db[database.ROLE]
        .find(query)
        .sort(page_request.sort_spec(ROLE_SORT_FIELDS, default="name"))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    return page_response([role_dto(doc) async for doc in cursor], total, page_request)


async def list_permissions(page_request: PageRequest) -> dict:
    total = await database.db[database.PERMISSION].count_documents({})
    cursor = (
        database.db[database.PERMISSION]
        .find({})
        .sort(page_request.sort_spec(PERMISSION_SORT_FIELDS, default="code"))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = [
        {"code": doc["_id"], "category": doc["category"], "description": doc["description"]}
        async for doc in cursor
    ]
    return page_response(items, total, page_request)


def _validate_permission_codes(codes: list[str]) -> None:
    unknown = sorted(set(codes) - set(database.ALL_PERMISSIONS))
    if unknown:
        raise AppError(
            "VALIDATION-001",
            details=[{"field": "permissions", "issue": f"Unknown permission codes: {unknown}"}],
        )
    if len(codes) > settings.MAX_PERMISSIONS_PER_ROLE:
        raise AppError(
            "VALIDATION-001",
            details=[{"field": "permissions", "issue": f"At most {settings.MAX_PERMISSIONS_PER_ROLE} permissions."}],
        )


async def _assert_custom_roles_allowed(workspace_id: str) -> None:
    workspace = await database.db[database.WORKSPACE].find_one({"_id": workspace_id, "deleted_at": None})
    if not workspace:
        raise AppError("WORKSPACE-001")
    if workspace["plan"] not in CUSTOM_ROLE_PLANS:
        raise AppError("AUTHZ-001", "Custom roles are available on the PRO and ENTERPRISE plans.")


async def _get_scoped_role(context: AuthContext, role_id: str) -> dict:
    role = await database.db[database.ROLE].find_one({"_id": role_id, "deleted_at": None})
    if not role:
        raise AppError("WORKSPACE-008")
    if role["workspace_id"] != context.workspace_id:
        raise AppError("WORKSPACE-007")
    return role


async def create_role(context: AuthContext, payload, request: Request) -> dict:
    await _assert_custom_roles_allowed(context.workspace_id)
    _validate_permission_codes(payload.permissions)

    if payload.name in database.SYSTEM_ROLE_PERMISSIONS:
        raise AppError("WORKSPACE-011", "That name is reserved for a default role.")

    total = await database.db[database.ROLE].count_documents(
        {"workspace_id": context.workspace_id, "deleted_at": None}
    )
    if total >= settings.MAX_CUSTOM_ROLES:
        raise AppError("WORKSPACE-009")
    if await database.db[database.ROLE].find_one(
        {"workspace_id": context.workspace_id, "name": payload.name, "deleted_at": None}
    ):
        raise AppError("WORKSPACE-009", "A role with that name already exists.")

    now = utc_now()
    role = {
        "_id": new_id(),
        "workspace_id": context.workspace_id,
        "name": payload.name,
        "description": payload.description,
        "permissions": sorted(set(payload.permissions)),
        "is_system": False,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.ROLE].insert_one(role)
    await audit.record(
        action="ROLE_CREATED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="ROLE",
        resource_id=role["_id"],
        request=request,
        metadata={"name": payload.name, "permissions": role["permissions"]},
    )
    return role_dto(role)


async def update_role(context: AuthContext, role_id: str, payload, request: Request) -> dict:
    role = await _get_scoped_role(context, role_id)
    if role.get("is_system"):
        raise AppError("WORKSPACE-011")

    updates: dict = {}
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.permissions is not None:
        _validate_permission_codes(payload.permissions)
        updates["permissions"] = sorted(set(payload.permissions))
    if not updates:
        return role_dto(role)

    updates["updated_at"] = utc_now()
    await database.db[database.ROLE].update_one({"_id": role_id}, {"$set": updates})
    await audit.record(
        action="ROLE_UPDATED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="ROLE",
        resource_id=role_id,
        request=request,
        metadata={"fields": sorted(updates.keys())},
    )
    return role_dto(await database.db[database.ROLE].find_one({"_id": role_id}))


async def delete_role(context: AuthContext, role_id: str, request: Request) -> None:
    role = await _get_scoped_role(context, role_id)
    if role.get("is_system"):
        raise AppError("WORKSPACE-011")
    in_use = await database.db[database.WORKSPACE_MEMBER].count_documents(
        {"workspace_id": context.workspace_id, "roles": role["name"], "status": "ACTIVE", "deleted_at": None}
    )
    if in_use:
        raise AppError("WORKSPACE-009", "This role is still assigned to members.")

    now = utc_now()
    await database.db[database.ROLE].update_one({"_id": role_id}, {"$set": {"deleted_at": now, "updated_at": now}})
    await audit.record(
        action="ROLE_DELETED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="ROLE",
        resource_id=role_id,
        request=request,
        metadata={"name": role["name"]},
    )
