"""Role and permission DTOs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ROLE_NAME_PATTERN = r"^[A-Z][A-Z0-9_]{1,31}$"


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    permissions: list[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime


class RolePage(BaseModel):
    items: list[RoleResponse]
    page: int
    size: int
    total: int
    total_pages: int


class RoleCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(pattern=ROLE_NAME_PATTERN)
    description: str | None = Field(default=None, max_length=200)
    permissions: list[str] = Field(min_length=1, max_length=200)


class RoleUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = Field(default=None, max_length=200)
    permissions: list[str] | None = Field(default=None, min_length=1, max_length=200)


class PermissionResponse(BaseModel):
    code: str
    category: str
    description: str


class PermissionPage(BaseModel):
    items: list[PermissionResponse]
    page: int
    size: int
    total: int
    total_pages: int
