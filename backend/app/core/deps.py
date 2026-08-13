"""Authentication / authorization dependencies.

`workspace_id` and `user_id` are always derived from the verified access token
and the workspace membership row — never from the request body or query string.
Permissions are re-resolved from the database on every request rather than
trusted from the JWT claim.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import db as database
from app.core.config import settings
from app.core.errors import AppError
from app.core.models import utc_now
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user_id: str
    email: str
    full_name: str
    session_id: str
    workspace_id: str | None
    role: str | None
    permissions: list[str] = field(default_factory=list)
    is_owner: bool = False

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise AppError("AUTHZ-001")


async def resolve_membership(user_id: str, workspace_id: str) -> dict:
    member = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"workspace_id": workspace_id, "user_id": user_id, "status": "ACTIVE", "deleted_at": None}
    )
    if not member:
        raise AppError("WORKSPACE-002")
    return member


async def resolve_permissions(workspace_id: str, role_names: list[str]) -> list[str]:
    permissions: set[str] = set()
    cursor = database.db[database.ROLE].find(
        {"workspace_id": workspace_id, "name": {"$in": role_names}, "deleted_at": None}
    )
    async for role in cursor:
        permissions.update(role.get("permissions", []))
    return sorted(permissions)


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if credentials is None or not credentials.credentials:
        raise AppError("AUTH-003")

    claims = decode_access_token(credentials.credentials)
    session = await database.db[database.SESSION].find_one({"_id": claims.get("session_id")})
    if not session or session.get("revoked"):
        raise AppError("AUTH-006")

    now = utc_now()
    expires_at = session["expires_at"]
    last_activity = session.get("last_activity") or session["created_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=now.tzinfo)

    if expires_at <= now or (now - last_activity) > timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES):
        await database.db[database.SESSION].update_one(
            {"_id": session["_id"]}, {"$set": {"revoked": True, "updated_at": now}}
        )
        raise AppError("AUTH-006")

    user = await database.db[database.USER].find_one({"_id": claims["user_id"], "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    locked_until = user.get("locked_until")
    if locked_until:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=now.tzinfo)
        if locked_until > now:
            raise AppError("AUTH-005")
    if user["status"] in {"DISABLED", "DELETED"}:
        raise AppError("AUTH-011")
    if user.get("email_verified_at") is None:
        raise AppError("AUTH-004")

    await database.db[database.SESSION].update_one(
        {"_id": session["_id"]}, {"$set": {"last_activity": now, "updated_at": now}}
    )

    workspace_id = session.get("workspace_id")
    role, permissions, is_owner = None, [], False
    if workspace_id:
        member = await resolve_membership(user["_id"], workspace_id)
        workspace = await database.db[database.WORKSPACE].find_one({"_id": workspace_id, "deleted_at": None})
        if not workspace:
            raise AppError("WORKSPACE-001")
        if workspace["status"] != "ACTIVE":
            raise AppError("WORKSPACE-002")
        role_names = member.get("roles", [])
        role = role_names[0] if role_names else None
        permissions = await resolve_permissions(workspace_id, role_names)
        is_owner = workspace["owner_id"] == user["_id"]

    return AuthContext(
        user_id=user["_id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        session_id=session["_id"],
        workspace_id=workspace_id,
        role=role,
        permissions=permissions,
        is_owner=is_owner,
    )


def require_permission(permission: str):
    async def _dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if context.workspace_id is None:
            raise AppError("WORKSPACE-002")
        context.require(permission)
        return context

    return _dependency


async def require_owner(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if context.workspace_id is None or not context.is_owner:
        raise AppError("WORKSPACE-006")
    return context


def assert_same_workspace(context: AuthContext, resource_workspace_id: str | None) -> None:
    """Guard for any resource fetched by id: it must belong to the token's workspace."""
    if resource_workspace_id != context.workspace_id:
        raise AppError("WORKSPACE-007")
