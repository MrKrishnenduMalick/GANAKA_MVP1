"""Ganaka Core Platform Service — application entry point.

Preserved from the previous scaffold: the FastAPI app object, the `/api` router
mount and the CORS middleware. Added for Milestone 1: the versioned `/api/v1`
router tree (auth, workspace, RBAC), request-id propagation, the canonical error
envelope and the idempotent schema bootstrap.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware
from typing import List
import uuid

from app.core import db as database
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.models import new_id
from app.modules.auth.router import router as auth_router
from app.modules.rbac.router import router as rbac_router
from app.modules.shopify.router import (
    dashboard_router,
    exports_router,
    health_router,
    notifications_router,
    razorpay_router,
    reconciliation_router,
    router as shopify_router,
)
from app.modules.workspace.router import router as workspace_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = database.client
db = database.db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.bootstrap()
    yield
    client.close()


app = FastAPI(
    title="Ganaka Core Platform Service",
    description="Financial reconciliation platform for Shopify-based D2C businesses.",
    version="1.0.0",
    lifespan=lifespan,
)

# Legacy scaffold router (kept for backward compatibility).
api_router = APIRouter(prefix="/api")

# Versioned API surface (RULE API-001).
v1_router = APIRouter(prefix=settings.API_PREFIX)


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


v1_router.include_router(auth_router)
v1_router.include_router(workspace_router)
v1_router.include_router(rbac_router)
v1_router.include_router(shopify_router)
v1_router.include_router(razorpay_router)
v1_router.include_router(reconciliation_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(exports_router)
v1_router.include_router(notifications_router)
v1_router.include_router(health_router)

app.include_router(api_router)
app.include_router(v1_router)

register_exception_handlers(app)

# ARCH-AUDIT-011 fix: origins are resolved once in app.core.config
# (settings.CORS_ORIGINS) so a wildcard is never combined with
# allow_credentials=True. Do not read CORS_ORIGINS from the environment here.
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or new_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
