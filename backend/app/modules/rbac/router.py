"""Role and permission controllers."""

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.deps import AuthContext, require_permission
from app.core.pagination import PageRequest
from app.modules.rbac import service
from app.modules.rbac.schemas import (
    PermissionPage,
    RoleCreateRequest,
    RolePage,
    RoleResponse,
    RoleUpdateRequest,
)

router = APIRouter(tags=["RBAC"])


@router.get(
    "/roles",
    response_model=RolePage,
    summary="List roles in the current workspace",
    description="Requires workspace.read. Paginated (page/size/sort).",
)
async def list_roles(
    page_request: PageRequest = Depends(),
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    return await service.list_roles(context, page_request)


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
    description="Requires workspace.members. Custom roles need the PRO or ENTERPRISE plan.",
)
async def create_role(
    payload: RoleCreateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    return await service.create_role(context, payload, request)


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update a custom role",
    description="Requires workspace.members. Default (system) roles are immutable.",
)
async def update_role(
    role_id: str,
    payload: RoleUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    return await service.update_role(context, role_id, payload, request)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom role",
    description="Requires workspace.members. Roles still assigned to members cannot be deleted.",
)
async def delete_role(
    role_id: str,
    request: Request,
    context: AuthContext = Depends(require_permission("workspace.members")),
):
    await service.delete_role(context, role_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/permissions",
    response_model=PermissionPage,
    summary="List the permission catalog",
    description="Requires workspace.read. Paginated (page/size/sort).",
)
async def list_permissions(
    page_request: PageRequest = Depends(),
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    return await service.list_permissions(page_request)
