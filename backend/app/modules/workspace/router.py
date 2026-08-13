"""Workspace, membership and invitation controllers."""

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core import db as database
from app.core.deps import AuthContext, get_auth_context, require_owner, require_permission
from app.core.errors import AppError
from app.core.pagination import PageRequest
from app.core.rate_limit import enforce
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import MessageResponse, TokenResponse, WorkspaceSummary
from app.modules.auth.router import _set_refresh_cookie
from app.modules.workspace import service
from app.modules.workspace.schemas import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationResponse,
    MemberPage,
    MemberResponse,
    MemberUpdateRequest,
    TransferOwnershipRequest,
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdateRequest,
    WorkspaceUpdateRequest,
)

router = APIRouter(prefix="/workspaces", tags=["Workspace"])


def _workspace_response(workspace: dict) -> dict:
    return {
        "id": workspace["_id"],
        "name": workspace["name"],
        "slug": workspace["slug"],
        "status": workspace["status"],
        "plan": workspace["plan"],
        "timezone": workspace["timezone"],
        "currency": workspace["currency"],
        "owner_id": workspace["owner_id"],
        "created_at": workspace["created_at"],
        "updated_at": workspace["updated_at"],
    }


@router.get("", response_model=list[WorkspaceSummary], summary="Workspaces the current user belongs to")
async def list_workspaces(context: AuthContext = Depends(get_auth_context)):
    return await service.list_workspaces_for_user(context.user_id)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an additional workspace owned by the current user",
)
async def create_workspace(
    payload: WorkspaceCreateRequest, request: Request, context: AuthContext = Depends(get_auth_context)
):
    user = await database.db[database.USER].find_one({"_id": context.user_id, "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    workspace = await service.create_workspace(owner=user, name=payload.name, request=request)
    updates = {key: value for key, value in {"timezone": payload.timezone, "currency": payload.currency}.items() if value}
    if updates:
        await database.db[database.WORKSPACE].update_one({"_id": workspace["_id"]}, {"$set": updates})
        workspace = await database.db[database.WORKSPACE].find_one({"_id": workspace["_id"]})
    return _workspace_response(workspace)


# --- Literal member/invitation routes are declared before /{workspace_id} ---


@router.get(
    "/members",
    response_model=MemberPage,
    summary="List members of the current workspace",
    description="Requires workspace.read. Paginated (page/size/sort), filter by status.",
)
async def list_members(
    page_request: PageRequest = Depends(),
    member_status: str | None = Query(None, alias="status", pattern="^(INVITED|PENDING|ACTIVE|SUSPENDED|REMOVED)$"),
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    return await service.list_members(context, page_request, member_status)


@router.post(
    "/members",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member by inviting them",
    description="Requires workspace.members. Membership is only created once the invitation is accepted.",
)
async def add_member(
    payload: InvitationCreateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    await enforce("workspace.invite", request, subject=context.workspace_id)
    return await service.invite_member(context, payload.email, payload.role, request)


@router.patch(
    "/members/{member_id}",
    response_model=MemberResponse,
    summary="Change a member's roles",
    description="Requires workspace.members.",
)
async def update_member(
    member_id: str,
    payload: MemberUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    return await service.update_member(context, member_id, payload.roles, request)


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
    description="Requires workspace.members. The owner can never be removed.",
)
async def remove_member(
    member_id: str,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    await service.remove_member(context, member_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to the current workspace",
    description="Requires workspace.members.",
)
async def create_invitation(
    payload: InvitationCreateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    await enforce("workspace.invite", request, subject=context.workspace_id)
    return await service.invite_member(context, payload.email, payload.role, request)


@router.post(
    "/invitations/accept",
    response_model=WorkspaceSummary,
    summary="Accept a workspace invitation",
    description="Requires authentication. The invitation must match the authenticated user's email.",
)
async def accept_invitation(
    payload: InvitationAcceptRequest, request: Request, context: AuthContext = Depends(get_auth_context)
):
    user = await database.db[database.USER].find_one({"_id": context.user_id, "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    return await service.accept_invitation(user=user, raw_token=payload.token, request=request)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get a workspace",
    description="Requires workspace.read. Only the workspace bound to the access token can be read.",
)
async def get_workspace(workspace_id: str, context: AuthContext = Depends(require_permission("workspace.read"))):
    workspace = await service.get_workspace_scoped(context, workspace_id)
    return _workspace_response(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update a workspace",
    description="Requires workspace.update. Changing status additionally requires ownership.",
)
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.update")),
):
    workspace = await service.update_workspace(context, workspace_id, payload.model_dump(), request)
    return _workspace_response(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete a workspace",
    description="Owner only. Financial records are never removed; the workspace is marked DELETED.",
)
async def delete_workspace(
    workspace_id: str, request: Request, context: AuthContext = Depends(require_owner)
):
    await service.delete_workspace(context, workspace_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{workspace_id}/settings",
    response_model=WorkspaceSettingsResponse,
    summary="Get workspace settings",
    description="Requires workspace.read.",
)
async def get_settings(workspace_id: str, context: AuthContext = Depends(require_permission("workspace.read"))):
    return await service.get_settings(context, workspace_id)


@router.patch(
    "/{workspace_id}/settings",
    response_model=WorkspaceSettingsResponse,
    summary="Update workspace settings",
    description="Requires workspace.settings.",
)
async def update_settings(
    workspace_id: str,
    payload: WorkspaceSettingsUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.settings")),
):
    return await service.update_settings(context, workspace_id, payload.model_dump(), request)


@router.post(
    "/{workspace_id}/switch",
    response_model=TokenResponse,
    summary="Switch the active workspace",
    description="Requires authentication and active membership of the target workspace. Reissues the "
    "access token and rotates the refresh token so both are scoped to the new workspace.",
)
async def switch_workspace(
    workspace_id: str, request: Request, response: Response, context: AuthContext = Depends(get_auth_context)
):
    user = await database.db[database.USER].find_one({"_id": context.user_id, "deleted_at": None})
    if not user:
        raise AppError("AUTH-007")
    workspace = await database.db[database.WORKSPACE].find_one(
        {"_id": workspace_id, "deleted_at": None, "status": "ACTIVE"}
    )
    if not workspace:
        raise AppError("WORKSPACE-001")
    member = await database.db[database.WORKSPACE_MEMBER].find_one(
        {"workspace_id": workspace_id, "user_id": context.user_id, "status": "ACTIVE", "deleted_at": None}
    )
    if not member:
        raise AppError("WORKSPACE-002")

    result, raw_refresh = await auth_service.issue_session_tokens(
        user=user, workspace_id=workspace_id, request=request, reuse_session_id=context.session_id
    )
    await database.db[database.USER].update_one(
        {"_id": context.user_id}, {"$set": {"default_workspace_id": workspace_id}}
    )
    _set_refresh_cookie(response, raw_refresh)
    return result


@router.post(
    "/{workspace_id}/transfer-ownership",
    response_model=WorkspaceSummary,
    summary="Transfer workspace ownership",
    description="Owner only. The previous owner is downgraded to ADMIN so the workspace is never ownerless.",
)
async def transfer_ownership(
    workspace_id: str,
    payload: TransferOwnershipRequest,
    request: Request,
    context: AuthContext = Depends(require_owner),
):
    return await service.transfer_ownership(context, workspace_id, payload.new_owner_user_id, request)
