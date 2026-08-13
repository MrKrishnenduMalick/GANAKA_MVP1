"""Shopify OAuth business logic (Feature 2.1)."""

import asyncio
import csv
import hashlib
import hmac
import io
import json
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from bson import Binary
from fastapi import Request
from pymongo import DESCENDING

from app.core import audit
from app.core import db as database
from app.core import crypto
from app.core.config import settings
from app.core.deps import AuthContext
from app.core.errors import AppError
from app.core.models import new_id, utc_now
from app.core.pagination import page_response
from app.core.security import hash_token
from app.modules.shopify.schemas import ExportRequest, NotificationPreferenceUpdate
from app.services import email as email_service

logger = logging.getLogger("ganaka.shopify")

SHOPIFY_OAUTH_AUTHORIZE_URL = "https://{shop}/admin/oauth/authorize"
SHOPIFY_OAUTH_TOKEN_URL = "https://{shop}/admin/oauth/access_token"
SHOPIFY_SHOP_URL = "https://{shop}/admin/api/2024-01/shop.json"


def _require_configured() -> None:
    if not settings.shopify_configured:
        raise AppError("EXTERNAL-001", "Shopify integration is not configured on this deployment.")


def _connection_dto(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "workspace_id": doc["workspace_id"],
        "shop_domain": doc["shop_domain"],
        "shop_name": doc["shop_name"],
        "scopes": doc["scopes"],
        "status": doc["status"],
        "installed_at": doc["installed_at"],
        "disconnected_at": doc.get("disconnected_at"),
        "last_verified_at": doc.get("last_verified_at"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


async def generate_install_url(context: AuthContext, shop_domain: str) -> dict:
    _require_configured()
    existing = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if existing:
        raise AppError("SHOPIFY-005")
    return {"install_url": _build_install_url(context, shop_domain)}


async def _build_install_url(context: AuthContext, shop_domain: str) -> str:
    raw_state = secrets.token_urlsafe(32)
    now = utc_now()
    await database.db[database.SHOPIFY_OAUTH_STATE].insert_one(
        {
            "_id": new_id(),
            "workspace_id": context.workspace_id,
            "state_hash": hash_token(raw_state),
            "expires_at": now + timedelta(minutes=settings.SHOPIFY_OAUTH_STATE_TTL_MINUTES),
            "used_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    params = {
        "client_id": settings.SHOPIFY_API_KEY,
        "scope": settings.SHOPIFY_SCOPES,
        "redirect_uri": f"{settings.SHOPIFY_APP_URL}/api/v1/shopify/callback",
        "state": raw_state,
    }
    return f"{SHOPIFY_OAUTH_AUTHORIZE_URL.format(shop=shop_domain)}?{urlencode(params)}"


def _verify_callback_hmac(query: dict) -> None:
    """Verify the OAuth callback HMAC (SEC-021 constant-time comparison)."""
    message = "&".join(f"{k}={v}" for k, v in sorted(query.items()) if k != "hmac")
    expected = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, query.get("hmac", "")):
        raise AppError("SHOPIFY-003")


async def _consume_state(state: str, workspace_id: str) -> None:
    """Validate and single-use consume the OAuth state nonce."""
    doc = await database.db[database.SHOPIFY_OAUTH_STATE].find_one(
        {"state_hash": hash_token(state), "used_at": None}
    )
    if not doc:
        raise AppError("SHOPIFY-004")
    now = utc_now()
    expires_at = doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise AppError("SHOPIFY-004")
    if doc["workspace_id"] != workspace_id:
        raise AppError("SHOPIFY-004")
    await database.db[database.SHOPIFY_OAUTH_STATE].update_one(
        {"_id": doc["_id"]}, {"$set": {"used_at": now, "updated_at": now}}
    )


async def _exchange_code(shop_domain: str, code: str) -> str:
    """Exchange the authorization code for an access token."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                SHOPIFY_OAUTH_TOKEN_URL.format(shop=shop_domain),
                json={
                    "client_id": settings.SHOPIFY_API_KEY,
                    "client_secret": settings.SHOPIFY_API_SECRET,
                    "code": code,
                },
            )
    except httpx.HTTPError:
        raise AppError("SHOPIFY-003")
    if response.status_code != 200:
        raise AppError("SHOPIFY-003")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise AppError("SHOPIFY-003")
    return token


async def _verify_shop(shop_domain: str, access_token: str) -> dict:
    """Validate the store and return its shop metadata."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                SHOPIFY_SHOP_URL.format(shop=shop_domain),
                headers={"X-Shopify-Access-Token": access_token},
            )
    except httpx.HTTPError:
        raise AppError("SHOPIFY-008")
    if response.status_code != 200:
        raise AppError("SHOPIFY-008")
    shop = response.json().get("shop", {})
    if not shop:
        raise AppError("SHOPIFY-008")
    return shop


async def handle_callback(context: AuthContext, query: dict, request: Request) -> dict:
    _require_configured()
    _verify_callback_hmac(query)
    await _consume_state(query["state"], context.workspace_id)

    existing = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if existing:
        raise AppError("SHOPIFY-005")

    access_token = await _exchange_code(query["shop"], query["code"])
    shop = await _verify_shop(query["shop"], access_token)

    now = utc_now()
    connection = {
        "_id": new_id(),
        "workspace_id": context.workspace_id,
        "shop_domain": query["shop"],
        "shop_name": shop.get("name") or query["shop"],
        "access_token_encrypted": crypto.encrypt(access_token),
        "scopes": settings.SHOPIFY_SCOPES,
        "installed_at": now,
        "status": "ACTIVE",
        "disconnected_at": None,
        "last_verified_at": now,
        "metadata": {"shop_currency": shop.get("currency"), "shop_plan": shop.get("plan_name")},
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.SHOPIFY_CONNECTION].insert_one(connection)
    await audit.record(
        action="SHOPIFY_CONNECTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_CONNECTION",
        resource_id=connection["_id"],
        request=request,
        metadata={"shop_domain": query["shop"]},
    )
    return _connection_dto(connection)


async def get_status(context: AuthContext) -> dict:
    """Return the workspace's active Shopify connection, if any."""
    doc = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        return {"connected": False, "connection": None}
    return {"connected": True, "connection": _connection_dto(doc)}


async def disconnect(context: AuthContext, request: Request) -> dict:
    """Disconnect the workspace's Shopify store (allows reconnect)."""
    doc = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        raise AppError("SHOPIFY-006")
    now = utc_now()
    await database.db[database.SHOPIFY_CONNECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "DISCONNECTED", "disconnected_at": now, "updated_at": now}},
    )
    await audit.record(
        action="SHOPIFY_DISCONNECTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_CONNECTION",
        resource_id=doc["_id"],
        request=request,
        metadata={"shop_domain": doc["shop_domain"]},
    )
    return {"message": "Shopify store disconnected."}


# --- Feature 2.2: Initial data synchronization ---

SHOPIFY_API_VERSION = "2024-01"
SYNC_RESOURCES = ("orders", "products", "customers")


async def _get_connection(context: AuthContext) -> dict:
    """Return the active connection with the decrypted access token."""
    doc = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        raise AppError("SHOPIFY-006")
    try:
        token = crypto.decrypt(doc["access_token_encrypted"])
    except crypto.CryptoError:
        raise AppError("SHOPIFY-008")
    return {**doc, "access_token": token}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _order_dto(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "shopify_id": doc["shopify_id"],
        "order_number": doc.get("order_number"),
        "customer_id": doc.get("customer_id"),
        "currency": doc.get("currency"),
        "subtotal": doc.get("subtotal", 0.0),
        "tax": doc.get("tax", 0.0),
        "shipping": doc.get("shipping", 0.0),
        "discount": doc.get("discount", 0.0),
        "total": doc.get("total", 0.0),
        "status": doc.get("status"),
        "financial_status": doc.get("financial_status"),
        "fulfillment_status": doc.get("fulfillment_status"),
        "payment_gateway_names": doc.get("payment_gateway_names", []),
        "presentment_currency": doc.get("presentment_currency"),
        "gift_card_amount_used": doc.get("gift_card_amount_used", 0.0),
        "shopify_created_at": doc.get("shopify_created_at"),
        "shopify_updated_at": doc.get("shopify_updated_at"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def _product_dto(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "shopify_id": doc["shopify_id"],
        "title": doc["title"],
        "handle": doc.get("handle"),
        "product_type": doc.get("product_type"),
        "vendor": doc.get("vendor"),
        "status": doc.get("status"),
        "shopify_created_at": doc.get("shopify_created_at"),
        "shopify_updated_at": doc.get("shopify_updated_at"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def _customer_dto(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "shopify_id": doc["shopify_id"],
        "email": doc.get("email"),
        "first_name": doc.get("first_name"),
        "last_name": doc.get("last_name"),
        "phone": doc.get("phone"),
        "tags": doc.get("tags", []),
        "shopify_created_at": doc.get("shopify_created_at"),
        "shopify_updated_at": doc.get("shopify_updated_at"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def _order_doc(workspace_id: str, order: dict) -> dict:
    """Map a Shopify order payload to the stored document (ORDER_FIELDS)."""
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "shopify_id": order.get("id"),
        "order_number": order.get("order_number"),
        "customer_id": (order.get("customer") or {}).get("id"),
        "currency": order.get("currency"),
        "subtotal": float(order.get("subtotal_price") or 0.0),
        "tax": float(order.get("total_tax") or 0.0),
        "shipping": float((order.get("total_shipping_price_set") or {}).get("shop_money", {}).get("amount") or 0.0),
        "discount": float(order.get("total_discounts") or 0.0),
        "total": float(order.get("total_price") or 0.0),
        "status": order.get("status"),
        "financial_status": order.get("financial_status"),
        "fulfillment_status": order.get("fulfillment_status"),
        # implementation/04 ORDER_FIELDS: payment_gateway_names stored verbatim,
        # never null — ["unknown"] if Shopify returns an empty array.
        "payment_gateway_names": order.get("payment_gateway_names") or ["unknown"],
        "presentment_currency": order.get("presentment_currency"),
        # BR-034: gift_card_amount_used default 0.00.
        "gift_card_amount_used": float(order.get("gift_card_amount_used") or 0.0),
        "shopify_created_at": _parse_iso(order.get("created_at")),
        "shopify_updated_at": _parse_iso(order.get("updated_at")),
        "raw": order,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def _product_doc(workspace_id: str, product: dict) -> dict:
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "shopify_id": product.get("id"),
        "title": product.get("title") or "",
        "handle": product.get("handle"),
        "product_type": product.get("product_type"),
        "vendor": product.get("vendor"),
        "status": product.get("status"),
        "shopify_created_at": _parse_iso(product.get("created_at")),
        "shopify_updated_at": _parse_iso(product.get("updated_at")),
        "raw": product,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def _customer_doc(workspace_id: str, customer: dict) -> dict:
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "shopify_id": customer.get("id"),
        "email": customer.get("email"),
        "first_name": customer.get("first_name"),
        "last_name": customer.get("last_name"),
        "phone": customer.get("phone"),
        "tags": customer.get("tags") or [],
        "shopify_created_at": _parse_iso(customer.get("created_at")),
        "shopify_updated_at": _parse_iso(customer.get("updated_at")),
        "raw": customer,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


async def _upsert_many(collection: str, docs: list[dict]) -> int:
    """Idempotent import: upsert by (workspace_id, shopify_id), never duplicate."""
    imported = 0
    for doc in docs:
        if doc.get("shopify_id") is None:
            continue
        result = await database.db[collection].update_one(
            {"workspace_id": doc["workspace_id"], "shopify_id": doc["shopify_id"]},
            {"$set": doc, "$setOnInsert": {"_id": new_id()}},
            upsert=True,
        )
        if result.upserted_id is not None:
            imported += 1
    return imported


async def _fetch_resource(connection: dict, resource: str, cursor: str | None = None) -> tuple[list[dict], str | None]:
    """Fetch one page of a Shopify resource. Returns (items, next_cursor)."""
    url = f"https://{connection['shop_domain']}/admin/api/{SHOPIFY_API_VERSION}/{resource}.json"
    params: dict = {"limit": 250}
    if cursor:
        params["page_info"] = cursor
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url, headers={"X-Shopify-Access-Token": connection["access_token"]}, params=params
            )
    except httpx.HTTPError:
        raise AppError("SHOPIFY-008")
    if response.status_code != 200:
        raise AppError("SHOPIFY-008")
    data = response.json()
    items = data.get(resource, [])
    next_cursor = None
    link = response.headers.get("Link", "")
    for part in link.split(","):
        if 'rel="next"' in part:
            start = part.find("page_info=") + len("page_info=")
            end = part.find(">", start)
            if start > len("page_info=") - 1 and end > start:
                next_cursor = part[start:end]
    return items, next_cursor


async def _sync_resource(connection: dict, workspace_id: str, resource: str) -> int:
    """Full initial sync of one resource with cursor pagination."""
    mapper = {"orders": _order_doc, "products": _product_doc, "customers": _customer_doc}[resource]
    collection = {
        "orders": database.SHOPIFY_ORDER,
        "products": database.SHOPIFY_PRODUCT,
        "customers": database.SHOPIFY_CUSTOMER,
    }[resource]
    imported = 0
    cursor = None
    while True:
        items, cursor = await _fetch_resource(connection, resource, cursor)
        if not items:
            break
        imported += await _upsert_many(collection, [mapper(workspace_id, item) for item in items])
        if not cursor:
            break
    return imported


async def run_sync(context: AuthContext, resources: list[str], request: Request) -> dict:
    """Run an initial full sync for the requested resources (manual sync)."""
    connection = await _get_connection(context)
    requested = [r for r in resources if r in SYNC_RESOURCES]
    if not requested:
        raise AppError("VALIDATION-001", details=[{"field": "resources", "issue": "No supported resources requested."}])

    now = utc_now()
    job_id = new_id()
    await database.db[database.SHOPIFY_SYNC_JOB].insert_one(
        {
            "_id": job_id,
            "workspace_id": context.workspace_id,
            "status": "RUNNING",
            "started_at": now,
            "completed_at": None,
            "error": None,
            "counts": {},
            "cursor": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    await audit.record(
        action="SHOPIFY_SYNC_STARTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_SYNC_JOB",
        resource_id=job_id,
        request=request,
        metadata={"resources": requested},
    )

    counts: dict = {}
    try:
        for resource in requested:
            counts[resource] = await _sync_resource(connection, context.workspace_id, resource)
        status = "COMPLETED"
        error = None
    except AppError as exc:
        status = "FAILED"
        error = exc.code
        counts = counts or {}

    await database.db[database.SHOPIFY_SYNC_JOB].update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": status,
                "completed_at": utc_now(),
                "error": error,
                "counts": counts,
                "updated_at": utc_now(),
            }
        },
    )
    await audit.record(
        action="SHOPIFY_SYNC_COMPLETED" if status == "COMPLETED" else "SHOPIFY_SYNC_FAILED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_SYNC_JOB",
        resource_id=job_id,
        request=request,
        metadata={"counts": counts, "error": error},
    )
    if status == "FAILED":
        # ARCH-AUDIT-003 fix: connect the failed_shopify_sync preference to a
        # real delivery attempt instead of leaving send_notification()
        # implemented but never called by anything.
        await send_notification(
            context,
            "failed_shopify_sync",
            {"title": "Shopify sync failed", "message": f"Shopify sync job {job_id} failed: {error}", "job_id": job_id},
        )
    return {"job_id": job_id, "status": status, "counts": counts}


async def get_sync_status(context: AuthContext, job_id: str) -> dict:
    """Return the status of a sync job (workspace-scoped)."""
    job = await database.db[database.SHOPIFY_SYNC_JOB].find_one({"_id": job_id})
    if not job or job["workspace_id"] != context.workspace_id:
        raise AppError("SHOPIFY-006")
    return {
        "job_id": job["_id"],
        "status": job["status"],
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at"),
        "error": job.get("error"),
        "counts": job.get("counts", {}),
    }


async def run_incremental_sync(context: AuthContext, request: Request) -> dict:
    """Run an incremental sync (manual trigger).

    ARCH-AUDIT-008 fix: this previously lived in the router (violating the
    module's own "no business logic in controllers" rule) and was a pure
    stub -- it inserted a RUNNING job document, never processed anything,
    never updated that document, and unconditionally returned
    "status": "COMPLETED", so the persisted job state and the API response
    permanently disagreed.

    There is no delta/cursor-based change feed implemented for Shopify in
    this codebase (catch-up between webhook deliveries is not tracked by a
    "since" token) -- the only currently-implemented resync mechanism is the
    same idempotent, upsert-by-shopify_id full sync used by run_sync(). So an
    "incremental" trigger here re-runs that same safe, idempotent sync for
    every supported resource: it is honest about what it actually does
    (a real, complete resync) rather than claiming a fake incremental delta.
    The job document written to Mongo always reflects the true outcome.
    """
    connection = await _get_connection(context)

    now = utc_now()
    job_id = new_id()
    await database.db[database.SHOPIFY_SYNC_JOB].insert_one(
        {
            "_id": job_id,
            "workspace_id": context.workspace_id,
            "status": "RUNNING",
            "started_at": now,
            "completed_at": None,
            "error": None,
            "counts": {},
            "cursor": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    await audit.record(
        action="SHOPIFY_INCREMENTAL_SYNC_STARTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_SYNC_JOB",
        resource_id=job_id,
        request=request,
        metadata={"resources": list(SYNC_RESOURCES)},
    )

    counts: dict = {}
    try:
        for resource in SYNC_RESOURCES:
            counts[resource] = await _sync_resource(connection, context.workspace_id, resource)
        status = "COMPLETED"
        error = None
    except AppError as exc:
        status = "FAILED"
        error = exc.code
        counts = counts or {}

    await database.db[database.SHOPIFY_SYNC_JOB].update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": status,
                "completed_at": utc_now(),
                "error": error,
                "counts": counts,
                "updated_at": utc_now(),
            }
        },
    )
    await audit.record(
        action="SHOPIFY_INCREMENTAL_SYNC_COMPLETED" if status == "COMPLETED" else "SHOPIFY_INCREMENTAL_SYNC_FAILED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="SHOPIFY_SYNC_JOB",
        resource_id=job_id,
        request=request,
        metadata={"counts": counts, "error": error},
    )
    if status == "FAILED":
        await send_notification(
            context,
            "failed_shopify_sync",
            {"title": "Shopify incremental sync failed", "message": f"Shopify sync job {job_id} failed: {error}", "job_id": job_id},
        )
    # The response mirrors exactly what was just persisted -- no more
    # hardcoded "COMPLETED" regardless of what actually happened.
    return {"job_id": job_id, "status": status, "counts": counts}


async def list_orders(context: AuthContext, page_request, financial_status: str | None, created_from, created_to) -> dict:
    """List the workspace's orders with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if financial_status:
        query["financial_status"] = financial_status
    if created_from or created_to:
        range_query: dict = {}
        if created_from:
            range_query["$gte"] = created_from
        if created_to:
            range_query["$lte"] = created_to
        query["shopify_created_at"] = range_query
    total = await database.db[database.SHOPIFY_ORDER].count_documents(query)
    cursor = (
        database.db[database.SHOPIFY_ORDER]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "shopify_created_at", "total"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = [_order_dto(doc) async for doc in cursor]
    return page_response(items, total, page_request)


async def list_products(context: AuthContext, page_request) -> dict:
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    total = await database.db[database.SHOPIFY_PRODUCT].count_documents(query)
    cursor = (
        database.db[database.SHOPIFY_PRODUCT]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "shopify_created_at", "title"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = [_product_dto(doc) async for doc in cursor]
    return page_response(items, total, page_request)


async def list_customers(context: AuthContext, page_request) -> dict:
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    total = await database.db[database.SHOPIFY_CUSTOMER].count_documents(query)
    cursor = (
        database.db[database.SHOPIFY_CUSTOMER]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "shopify_created_at", "email"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = [_customer_dto(doc) async for doc in cursor]
    return page_response(items, total, page_request)


# --- Feature 2.3: Webhooks & Incremental Sync ---

def _verify_webhook_hmac(payload: bytes, hmac_header: str | None) -> None:
    """Verify the Shopify webhook HMAC (constant-time comparison)."""
    if not hmac_header:
        raise AppError("SHOPIFY-007")
    expected = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, hmac_header):
        raise AppError("SHOPIFY-007")


def _payload_hash(payload: bytes) -> str:
    """SHA-256 hash of the raw payload for idempotency."""
    return hashlib.sha256(payload).hexdigest()


async def _resolve_workspace_for_shop(shop_domain: str) -> str | None:
    """Return the workspace_id for an active connection, or None."""
    doc = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"shop_domain": shop_domain, "status": "ACTIVE"}
    )
    return doc["workspace_id"] if doc else None


def _payload_shop_domain_consistent(topic: str, payload: bytes, claimed_shop_domain: str) -> bool:
    """ARCH-AUDIT-006 fix (partial mitigation): Shopify's webhook HMAC is
    computed with a single app-wide secret shared by every installed shop, so
    a valid (payload, HMAC) pair obtained from one connected shop's own
    webhook delivery does not, by itself, prove the payload belongs to the
    shop named in the X-Shopify-Shop-Domain header -- that header is
    otherwise trusted at face value. Where the payload carries its own
    embedded domain (order payloads include `order_status_url`, which points
    at the actual originating shop), cross-check it against the claimed
    header and reject on mismatch. This meaningfully raises the bar for
    replaying one shop's captured webhook against a different tenant's
    workspace for order events; it does not fully close the gap for topics
    whose payload carries no embedded domain (e.g. some product/customer
    payloads), which remains a residual, documented risk inherent to
    Shopify's app-secret-based (not per-shop-secret) webhook design.
    """
    if "orders" not in topic:
        return True  # no reliable embedded domain field on other topics
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return True  # let the JSON-parse step downstream raise a clear error
    status_url = data.get("order_status_url") or ""
    if not status_url:
        return True  # nothing to cross-check; don't reject on absence
    return claimed_shop_domain and claimed_shop_domain in status_url


async def process_webhook_event(payload: bytes, topic: str, shop_domain: str, event_id: str, hmac_header: str | None, request: Request) -> dict:
    """Verify, deduplicate, and process a Shopify webhook event."""
    _verify_webhook_hmac(payload, hmac_header)

    if not _payload_shop_domain_consistent(topic, payload, shop_domain):
        raise AppError("SHOPIFY-007")

    payload_hash = _payload_hash(payload)

    # Idempotency: reject duplicate payloads FOR THIS SHOP. Scoped by
    # shop_domain (ARCH-AUDIT-006 fix) so an identical payload arriving for a
    # different, unrelated shop is never silently dropped as a "duplicate".
    existing = await database.db[database.SHOPIFY_WEBHOOK_EVENT].find_one(
        {"shop_domain": shop_domain, "payload_hash": payload_hash}
    )
    if existing:
        return {"status": "duplicate", "event_id": existing["event_id"]}

    workspace_id = await _resolve_workspace_for_shop(shop_domain)
    if not workspace_id:
        await database.db[database.SHOPIFY_WEBHOOK_EVENT].insert_one(
            {
                "_id": new_id(),
                "event_id": event_id,
                "topic": topic,
                "shop_domain": shop_domain,
                "processed": False,
                "received_at": utc_now(),
                "payload_hash": payload_hash,
                "error": "NO_WORKSPACE",
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "deleted_at": None,
            }
        )
        await audit.record(
            action="SHOPIFY_WEBHOOK_REJECTED",
            actor_user_id=None,
            workspace_id=None,
            resource_type="SHOPIFY_WEBHOOK_EVENT",
            resource_id=event_id,
            request=request,
            metadata={"topic": topic, "shop_domain": shop_domain, "reason": "NO_WORKSPACE"},
        )
        return {"status": "rejected", "reason": "NO_WORKSPACE"}

    await database.db[database.SHOPIFY_WEBHOOK_EVENT].insert_one(
        {
            "_id": new_id(),
            "event_id": event_id,
            "topic": topic,
            "shop_domain": shop_domain,
            "processed": False,
            "received_at": utc_now(),
            "payload_hash": payload_hash,
            "error": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "deleted_at": None,
        }
    )

    await audit.record(
        action="SHOPIFY_WEBHOOK_RECEIVED",
        actor_user_id=None,
        workspace_id=workspace_id,
        resource_type="SHOPIFY_WEBHOOK_EVENT",
        resource_id=event_id,
        request=request,
        metadata={"topic": topic, "shop_domain": shop_domain},
    )

    try:
        counts = await _process_incremental_event(workspace_id, topic, payload)
        await database.db[database.SHOPIFY_WEBHOOK_EVENT].update_one(
            {"event_id": event_id},
            {"$set": {"processed": True, "updated_at": utc_now()}},
        )
        await audit.record(
            action="SHOPIFY_WEBHOOK_PROCESSED",
            actor_user_id=None,
            workspace_id=workspace_id,
            resource_type="SHOPIFY_WEBHOOK_EVENT",
            resource_id=event_id,
            request=request,
            metadata={"topic": topic, "counts": counts},
        )
        return {"status": "processed", "counts": counts}
    except AppError as exc:
        await database.db[database.SHOPIFY_WEBHOOK_EVENT].update_one(
            {"event_id": event_id},
            {"$set": {"processed": False, "error": exc.code, "updated_at": utc_now()}},
        )
        await audit.record(
            action="SHOPIFY_WEBHOOK_REJECTED",
            actor_user_id=None,
            workspace_id=workspace_id,
            resource_type="SHOPIFY_WEBHOOK_EVENT",
            resource_id=event_id,
            request=request,
            metadata={"topic": topic, "error": exc.code},
        )
        return {"status": "error", "error": exc.code}


async def _process_incremental_event(workspace_id: str, topic: str, payload: bytes) -> dict:
    """Apply a single webhook event to the local store (incremental sync)."""
    import json as _json
    try:
        data = _json.loads(payload)
    except _json.JSONDecodeError:
        raise AppError("VALIDATION-001", details=[{"field": "payload", "issue": "Invalid JSON"}])

    counts: dict = {}
    if topic in ("orders/create", "orders/updated", "orders/cancelled", "orders/fulfilled"):
        order = data.get("order") or data
        if order.get("id"):
            doc = _order_doc(workspace_id, order)
            await database.db[database.SHOPIFY_ORDER].update_one(
                {"workspace_id": workspace_id, "shopify_id": doc["shopify_id"]},
                {"$set": doc, "$setOnInsert": {"_id": new_id()}},
                upsert=True,
            )
            counts["orders"] = 1
    elif topic == "refunds/create":
        order = data.get("order") or data
        if order.get("id"):
            doc = _order_doc(workspace_id, order)
            await database.db[database.SHOPIFY_ORDER].update_one(
                {"workspace_id": workspace_id, "shopify_id": doc["shopify_id"]},
                {"$set": doc, "$setOnInsert": {"_id": new_id()}},
                upsert=True,
            )
            counts["orders"] = 1
    elif topic in ("products/create", "products/update"):
        product = data.get("product") or data
        if product.get("id"):
            doc = _product_doc(workspace_id, product)
            await database.db[database.SHOPIFY_PRODUCT].update_one(
                {"workspace_id": workspace_id, "shopify_id": doc["shopify_id"]},
                {"$set": doc, "$setOnInsert": {"_id": new_id()}},
                upsert=True,
            )
            counts["products"] = 1
    elif topic == "products/delete":
        product = data.get("product") or data
        if product.get("id"):
            now = utc_now()
            await database.db[database.SHOPIFY_PRODUCT].update_one(
                {"workspace_id": workspace_id, "shopify_id": product.get("id")},
                {"$set": {"deleted_at": now, "updated_at": now}},
            )
            counts["products"] = 1
    elif topic in ("customers/create", "customers/update"):
        customer = data.get("customer") or data
        if customer.get("id"):
            doc = _customer_doc(workspace_id, customer)
            await database.db[database.SHOPIFY_CUSTOMER].update_one(
                {"workspace_id": workspace_id, "shopify_id": doc["shopify_id"]},
                {"$set": doc, "$setOnInsert": {"_id": new_id()}},
                upsert=True,
            )
            counts["customers"] = 1
    else:
        counts["skipped"] = 1
    return counts


async def get_webhook_status(context: AuthContext) -> dict:
    """Return webhook event statistics for the workspace's shop."""
    connection = await database.db[database.SHOPIFY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not connection:
        raise AppError("SHOPIFY-006")

    shop_domain = connection["shop_domain"]
    total = await database.db[database.SHOPIFY_WEBHOOK_EVENT].count_documents({"shop_domain": shop_domain})
    processed = await database.db[database.SHOPIFY_WEBHOOK_EVENT].count_documents({"shop_domain": shop_domain, "processed": True})
    unprocessed = total - processed
    recent_cursor = (
        database.db[database.SHOPIFY_WEBHOOK_EVENT]
        .find({"shop_domain": shop_domain})
        .sort("received_at", DESCENDING)
        .limit(10)
    )
    recent = []
    async for doc in recent_cursor:
        recent.append(
            {
                "event_id": doc["event_id"],
                "topic": doc["topic"],
                "shop_domain": doc["shop_domain"],
                "processed": doc["processed"],
                "received_at": doc["received_at"],
                "error": doc.get("error"),
            }
        )
    return {"total": total, "processed": processed, "unprocessed": unprocessed, "recent": recent}


# --- Milestone 3: Razorpay Integration ---

RAZORPAY_API_VERSION = "v1"
RAZORPAY_BASE_URL = "https://api.razorpay.com"


def _require_razorpay_configured() -> None:
    if not settings.razorpay_configured:
        raise AppError("EXTERNAL-001", "Razorpay integration is not configured on this deployment.")


def _connection_dto_razorpay(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "workspace_id": doc["workspace_id"],
        "key_id": doc["key_id"],
        "account_name": doc.get("account_name"),
        "account_email": doc.get("account_email"),
        "status": doc["status"],
        "installed_at": doc["installed_at"],
        "disconnected_at": doc.get("disconnected_at"),
        "last_verified_at": doc.get("last_verified_at"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


async def _verify_razorpay_credentials(key_id: str, key_secret: str) -> None:
    """Validate the supplied credentials against the real Razorpay API before
    storing them (ARCH-AUDIT-001: each workspace connects its own account, so
    we must confirm the credentials actually work rather than trusting them
    blindly the way a platform-wide credential never needed to be checked)."""
    url = f"{RAZORPAY_BASE_URL}/{RAZORPAY_API_VERSION}/payments"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, auth=(key_id, key_secret), params={"count": 1})
    except httpx.HTTPError:
        raise AppError("RAZORPAY-008")
    if response.status_code == 401:
        raise AppError("RAZORPAY-009")
    if response.status_code != 200:
        raise AppError("RAZORPAY-008")


async def connect_razorpay(context: AuthContext, payload: "RazorpayConnectRequest", request: Request) -> dict:
    """Connect the workspace's OWN Razorpay account.

    ARCH-AUDIT-001 fix: credentials are supplied by the caller per workspace
    (never read from deployment-wide settings), verified against the live
    Razorpay API, and stored encrypted (AES-256-GCM). Each workspace only ever
    sees its own Razorpay account's data.
    """
    _require_razorpay_configured()
    existing = await database.db[database.RAZORPAY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if existing:
        raise AppError("RAZORPAY-005")

    await _verify_razorpay_credentials(payload.key_id, payload.key_secret)

    now = utc_now()
    connection = {
        "_id": new_id(),
        "workspace_id": context.workspace_id,
        "key_id": payload.key_id,
        "key_secret_encrypted": crypto.encrypt(payload.key_secret),
        "webhook_secret_encrypted": crypto.encrypt(payload.webhook_secret) if payload.webhook_secret else None,
        "account_name": None,
        "account_email": None,
        "installed_at": now,
        "status": "ACTIVE",
        "disconnected_at": None,
        "last_verified_at": now,
        "metadata": {},
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.RAZORPAY_CONNECTION].insert_one(connection)
    await audit.record(
        action="RAZORPAY_CONNECTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="RAZORPAY_CONNECTION",
        resource_id=connection["_id"],
        request=request,
        metadata={"key_id": payload.key_id},
    )
    return _connection_dto_razorpay(connection)


async def get_razorpay_status(context: AuthContext) -> dict:
    """Return the workspace's active Razorpay connection, if any."""
    doc = await database.db[database.RAZORPAY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        return {"connected": False, "connection": None}
    return {"connected": True, "connection": _connection_dto_razorpay(doc)}


async def disconnect_razorpay(context: AuthContext, request: Request) -> dict:
    """Disconnect the workspace's Razorpay account (allows reconnect)."""
    doc = await database.db[database.RAZORPAY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        raise AppError("RAZORPAY-006")
    now = utc_now()
    await database.db[database.RAZORPAY_CONNECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "DISCONNECTED", "disconnected_at": now, "updated_at": now}},
    )
    await audit.record(
        action="RAZORPAY_DISCONNECTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="RAZORPAY_CONNECTION",
        resource_id=doc["_id"],
        request=request,
        metadata={"key_id": doc["key_id"]},
    )
    return {"message": "Razorpay account disconnected."}


async def _get_razorpay_connection(context: AuthContext) -> dict:
    """Return the active connection with the decrypted key secret."""
    doc = await database.db[database.RAZORPAY_CONNECTION].find_one(
        {"workspace_id": context.workspace_id, "status": "ACTIVE"}
    )
    if not doc:
        raise AppError("RAZORPAY-006")
    try:
        key_secret = crypto.decrypt(doc["key_secret_encrypted"])
    except crypto.CryptoError:
        raise AppError("RAZORPAY-008")
    return {**doc, "key_secret": key_secret}


async def _active_razorpay_connections() -> list[dict]:
    """All ACTIVE Razorpay connections with decrypted webhook secrets.

    Used to resolve which workspace a Razorpay webhook belongs to (ARCH-AUDIT
    fix #8): unlike Shopify, Razorpay webhook payloads carry no per-tenant
    domain header, and each workspace now has its own key/secret pair (fix
    #1), so the connection whose *own* secret verifies the signature is the
    owner. This is an O(active connections) scan, acceptable at the product's
    stated 10-50 customer MVP scale; it should be revisited if that scale
    assumption changes.
    """
    connections = []
    cursor = database.db[database.RAZORPAY_CONNECTION].find(
        {"status": "ACTIVE", "webhook_secret_encrypted": {"$ne": None}}
    )
    async for doc in cursor:
        try:
            secret = crypto.decrypt(doc["webhook_secret_encrypted"])
        except crypto.CryptoError:
            continue
        connections.append({**doc, "webhook_secret": secret})
    return connections


async def _razorpay_get(connection: dict, path: str, params: dict | None = None) -> dict:
    """Make an authenticated GET request to the Razorpay API."""
    url = f"{RAZORPAY_BASE_URL}/{RAZORPAY_API_VERSION}/{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                auth=(connection["key_id"], connection["key_secret"]),
                params=params,
            )
    except httpx.HTTPError:
        raise AppError("RAZORPAY-008")
    if response.status_code != 200:
        raise AppError("RAZORPAY-008")
    return response.json()


def _payment_doc(workspace_id: str, payment: dict) -> dict:
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "razorpay_id": payment.get("id"),
        "order_id": payment.get("order_id"),
        "amount": float(payment.get("amount") or 0.0) / 100.0,
        "currency": payment.get("currency"),
        "status": payment.get("status"),
        "method": payment.get("method"),
        "fee": float(payment.get("fee") or 0.0) / 100.0,
        "tax": float(payment.get("tax") or 0.0) / 100.0,
        "captured": bool(payment.get("captured")),
        "refunded": bool(payment.get("refunded")),
        "razorpay_created_at": _parse_iso(payment.get("created_at")),
        "razorpay_updated_at": _parse_iso(payment.get("updated_at")),
        "raw": payment,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def _refund_doc(workspace_id: str, refund: dict) -> dict:
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "razorpay_id": refund.get("id"),
        "payment_id": refund.get("payment_id"),
        "amount": float(refund.get("amount") or 0.0) / 100.0,
        "currency": refund.get("currency"),
        "status": refund.get("status"),
        "reason": refund.get("reason"),
        "razorpay_created_at": _parse_iso(refund.get("created_at")),
        "razorpay_updated_at": _parse_iso(refund.get("updated_at")),
        "raw": refund,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def _settlement_doc(workspace_id: str, settlement: dict) -> dict:
    now = utc_now()
    return {
        "workspace_id": workspace_id,
        "razorpay_id": settlement.get("id"),
        "amount": float(settlement.get("amount") or 0.0) / 100.0,
        "currency": settlement.get("currency"),
        "status": settlement.get("status"),
        "fee": float(settlement.get("fee") or 0.0) / 100.0,
        "tax": float(settlement.get("tax") or 0.0) / 100.0,
        "settled_at": _parse_iso(settlement.get("created_at")),
        "razorpay_created_at": _parse_iso(settlement.get("created_at")),
        "razorpay_updated_at": _parse_iso(settlement.get("updated_at")),
        "raw": settlement,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


async def _upsert_razorpay_many(collection: str, docs: list[dict]) -> int:
    """Idempotent import: upsert by (workspace_id, razorpay_id), never duplicate."""
    imported = 0
    for doc in docs:
        if doc.get("razorpay_id") is None:
            continue
        result = await database.db[collection].update_one(
            {"workspace_id": doc["workspace_id"], "razorpay_id": doc["razorpay_id"]},
            {"$set": doc, "$setOnInsert": {"_id": new_id()}},
            upsert=True,
        )
        if result.upserted_id is not None:
            imported += 1
    return imported


async def sync_razorpay_payments(context: AuthContext, request: Request) -> dict:
    """Sync Razorpay payments (manual full sync)."""
    connection = await _get_razorpay_connection(context)
    data = await _razorpay_get(connection, "payments", {"count": 250})
    items = data.get("items", [])
    docs = [_payment_doc(context.workspace_id, item) for item in items]
    imported = await _upsert_razorpay_many(database.RAZORPAY_PAYMENT, docs)
    await audit.record(
        action="RAZORPAY_SYNC_STARTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="RAZORPAY_PAYMENT",
        resource_id=None,
        request=request,
        metadata={"count": imported},
    )
    return {"imported": imported}


async def sync_razorpay_refunds(context: AuthContext, request: Request) -> dict:
    """Sync Razorpay refunds (manual full sync)."""
    connection = await _get_razorpay_connection(context)
    data = await _razorpay_get(connection, "refunds", {"count": 250})
    items = data.get("items", [])
    docs = [_refund_doc(context.workspace_id, item) for item in items]
    imported = await _upsert_razorpay_many(database.RAZORPAY_REFUND, docs)
    await audit.record(
        action="RAZORPAY_SYNC_STARTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="RAZORPAY_REFUND",
        resource_id=None,
        request=request,
        metadata={"count": imported},
    )
    return {"imported": imported}


async def sync_razorpay_settlements(context: AuthContext, request: Request) -> dict:
    """Sync Razorpay settlements (manual full sync)."""
    connection = await _get_razorpay_connection(context)
    data = await _razorpay_get(connection, "settlements", {"count": 250})
    items = data.get("items", [])
    docs = [_settlement_doc(context.workspace_id, item) for item in items]
    imported = await _upsert_razorpay_many(database.RAZORPAY_SETTLEMENT, docs)
    await audit.record(
        action="RAZORPAY_SYNC_STARTED",
        actor_user_id=context.user_id,
        workspace_id=context.workspace_id,
        resource_type="RAZORPAY_SETTLEMENT",
        resource_id=None,
        request=request,
        metadata={"count": imported},
    )
    return {"imported": imported}


async def list_razorpay_payments(context: AuthContext, page_request, status: str | None, payment_id: str | None, order_id: str | None, date_from, date_to) -> dict:
    """List the workspace's Razorpay payments with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if status:
        query["status"] = status
    if payment_id:
        query["razorpay_id"] = payment_id
    if order_id:
        query["order_id"] = order_id
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    total = await database.db[database.RAZORPAY_PAYMENT].count_documents(query)
    cursor = (
        database.db[database.RAZORPAY_PAYMENT]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "razorpay_created_at", "amount"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = []
    async for doc in cursor:
        items.append(
            {
                "id": doc["_id"],
                "razorpay_id": doc["razorpay_id"],
                "order_id": doc.get("order_id"),
                "amount": doc.get("amount", 0.0),
                "currency": doc.get("currency"),
                "status": doc.get("status"),
                "method": doc.get("method"),
                "fee": doc.get("fee", 0.0),
                "tax": doc.get("tax", 0.0),
                "captured": doc.get("captured", False),
                "refunded": doc.get("refunded", False),
                "razorpay_created_at": doc.get("razorpay_created_at"),
                "razorpay_updated_at": doc.get("razorpay_updated_at"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
            }
        )
    return page_response(items, total, page_request)


async def list_razorpay_refunds(context: AuthContext, page_request, status: str | None, payment_id: str | None, date_from, date_to) -> dict:
    """List the workspace's Razorpay refunds with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if status:
        query["status"] = status
    if payment_id:
        query["payment_id"] = payment_id
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    total = await database.db[database.RAZORPAY_REFUND].count_documents(query)
    cursor = (
        database.db[database.RAZORPAY_REFUND]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "razorpay_created_at", "amount"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = []
    async for doc in cursor:
        items.append(
            {
                "id": doc["_id"],
                "razorpay_id": doc["razorpay_id"],
                "payment_id": doc.get("payment_id"),
                "amount": doc.get("amount", 0.0),
                "currency": doc.get("currency"),
                "status": doc.get("status"),
                "reason": doc.get("reason"),
                "razorpay_created_at": doc.get("razorpay_created_at"),
                "razorpay_updated_at": doc.get("razorpay_updated_at"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
            }
        )
    return page_response(items, total, page_request)


async def list_razorpay_settlements(context: AuthContext, page_request, status: str | None, date_from, date_to) -> dict:
    """List the workspace's Razorpay settlements with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if status:
        query["status"] = status
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    total = await database.db[database.RAZORPAY_SETTLEMENT].count_documents(query)
    cursor = (
        database.db[database.RAZORPAY_SETTLEMENT]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "razorpay_created_at", "amount"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = []
    async for doc in cursor:
        items.append(
            {
                "id": doc["_id"],
                "razorpay_id": doc["razorpay_id"],
                "amount": doc.get("amount", 0.0),
                "currency": doc.get("currency"),
                "status": doc.get("status"),
                "fee": doc.get("fee", 0.0),
                "tax": doc.get("tax", 0.0),
                "settled_at": doc.get("settled_at"),
                "razorpay_created_at": doc.get("razorpay_created_at"),
                "razorpay_updated_at": doc.get("razorpay_updated_at"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
            }
        )
    return page_response(items, total, page_request)


async def run_razorpay_sync(context: AuthContext, request: Request) -> dict:
    """Run a manual full sync for payments, refunds and settlements."""
    counts = {}
    counts["payments"] = (await sync_razorpay_payments(context, request))["imported"]
    counts["refunds"] = (await sync_razorpay_refunds(context, request))["imported"]
    counts["settlements"] = (await sync_razorpay_settlements(context, request))["imported"]
    return {"job_id": new_id(), "status": "COMPLETED", "counts": counts}


# --- ARCH-AUDIT-008 fix: Razorpay webhooks ---
#
# The DB schema already provisioned a razorpay_webhook_event collection with
# indexes (see db.py) but no receiver ever existed, so Razorpay data was only
# ever as fresh as the last manual sync. This adds real signature-verified
# webhook processing, mirroring the Shopify webhook pipeline's shape
# (verify -> dedupe -> resolve tenant -> apply -> audit).
#
# Razorpay webhook payloads carry no per-tenant identifier in a header the
# way Shopify's X-Shopify-Shop-Domain does. Because each workspace now has
# its own webhook secret (fix #1), the tenant is resolved by finding which
# active connection's secret makes the signature verify -- see
# _active_razorpay_connections(). This is O(active connections) per webhook,
# which is fine at the product's stated 10-50 customer scale.

RAZORPAY_WEBHOOK_EVENT_TYPES = {
    "payment.captured",
    "payment.failed",
    "refund.created",
    "refund.processed",
    "settlement.processed",
}


def _verify_razorpay_webhook_hmac(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _resolve_razorpay_workspace(payload: bytes, signature: str | None) -> tuple[str | None, str | None]:
    """Return (workspace_id, connection_id) for whichever active connection's
    webhook secret verifies the given signature, or (None, None)."""
    if not signature:
        return None, None
    for connection in await _active_razorpay_connections():
        if _verify_razorpay_webhook_hmac(payload, signature, connection["webhook_secret"]):
            return connection["workspace_id"], connection["_id"]
    return None, None


async def _process_razorpay_webhook_payload(workspace_id: str, event_type: str, data: dict) -> dict:
    """Apply a single verified Razorpay webhook event to the local store."""
    entity = (data.get("payload") or {}).get(event_type.split(".")[0], {}).get("entity", {})
    counts: dict = {}

    if event_type in ("payment.captured", "payment.failed"):
        if entity.get("id"):
            doc = _payment_doc(workspace_id, entity)
            imported = await _upsert_razorpay_many(database.RAZORPAY_PAYMENT, [doc])
            counts["payments"] = imported or 1
    elif event_type in ("refund.created", "refund.processed"):
        if entity.get("id"):
            doc = _refund_doc(workspace_id, entity)
            await _upsert_razorpay_many(database.RAZORPAY_REFUND, [doc])
            counts["refunds"] = 1
    elif event_type == "settlement.processed":
        if entity.get("id"):
            doc = _settlement_doc(workspace_id, entity)
            await _upsert_razorpay_many(database.RAZORPAY_SETTLEMENT, [doc])
            counts["settlements"] = 1
    else:
        counts["skipped"] = 1
    return counts


async def process_razorpay_webhook_event(payload: bytes, signature: str | None, request: Request) -> dict:
    """Verify, resolve tenant, deduplicate, and process a Razorpay webhook."""
    workspace_id, connection_id = await _resolve_razorpay_workspace(payload, signature)
    if not workspace_id:
        raise AppError("RAZORPAY-007")

    payload_hash = hashlib.sha256(payload).hexdigest()
    existing = await database.db[database.RAZORPAY_WEBHOOK_EVENT].find_one(
        {"workspace_id": workspace_id, "payload_hash": payload_hash}
    )
    if existing:
        return {"status": "duplicate", "event_id": existing["_id"]}

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise AppError("VALIDATION-001", details=[{"field": "payload", "issue": "Invalid JSON"}])
    event_type = data.get("event", "")

    now = utc_now()
    event_doc = {
        "_id": new_id(),
        "workspace_id": workspace_id,
        "connection_id": connection_id,
        "event_type": event_type,
        "payload_hash": payload_hash,
        "processed": False,
        "received_at": now,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.RAZORPAY_WEBHOOK_EVENT].insert_one(event_doc)
    await audit.record(
        action="RAZORPAY_WEBHOOK_RECEIVED",
        actor_user_id=None,
        workspace_id=workspace_id,
        resource_type="RAZORPAY_WEBHOOK_EVENT",
        resource_id=event_doc["_id"],
        request=request,
        metadata={"event_type": event_type},
    )

    try:
        counts = await _process_razorpay_webhook_payload(workspace_id, event_type, data)
        await database.db[database.RAZORPAY_WEBHOOK_EVENT].update_one(
            {"_id": event_doc["_id"]}, {"$set": {"processed": True, "updated_at": utc_now()}}
        )
        await audit.record(
            action="RAZORPAY_WEBHOOK_PROCESSED",
            actor_user_id=None,
            workspace_id=workspace_id,
            resource_type="RAZORPAY_WEBHOOK_EVENT",
            resource_id=event_doc["_id"],
            request=request,
            metadata={"event_type": event_type, "counts": counts},
        )
        return {"status": "processed", "counts": counts}
    except AppError as exc:
        await database.db[database.RAZORPAY_WEBHOOK_EVENT].update_one(
            {"_id": event_doc["_id"]}, {"$set": {"processed": False, "error": exc.code, "updated_at": utc_now()}}
        )
        await audit.record(
            action="RAZORPAY_WEBHOOK_REJECTED",
            actor_user_id=None,
            workspace_id=workspace_id,
            resource_type="RAZORPAY_WEBHOOK_EVENT",
            resource_id=event_doc["_id"],
            request=request,
            metadata={"event_type": event_type, "error": exc.code},
        )
        return {"status": "error", "error": exc.code}


# --- Milestone 4: Financial Reconciliation Engine ---

RECONCILIATION_MATCH_STATUSES = {
    "NOT_APPLICABLE",
    "MATCHED",
    "PARTIAL_MATCH",
    "GHOST_ORDER",
    "MISSING_PAYMENT",
    "DUPLICATE",
    "REFUND_MISMATCH",
    "SETTLEMENT_MISMATCH",
    "MANUAL_REVIEW",
}

# ARCH-AUDIT-009 fix: business-rule identifiers/descriptions for the
# "Business Rule" field the spec requires on every reconciliation result.
_BUSINESS_RULES = {
    "NOT_APPLICABLE": ("RULE-RECON-0", "Order was not paid through Razorpay; excluded from matching."),
    "DUPLICATE": ("RULE-RECON-3", "Duplicate Payments: more than one captured Razorpay payment references the same order."),
    "GHOST_ORDER": ("RULE-RECON-1", "Ghost Orders: no captured payment exists for an order older than the settlement window."),
    "MISSING_PAYMENT": ("RULE-RECON-2", "Missing Payments: no captured payment found yet, order is still within the settlement window."),
    "SETTLEMENT_MISMATCH": ("RULE-RECON-6", "Settlement Difference: a captured payment has no matching settlement within the settlement window."),
    "REFUND_MISMATCH": ("RULE-RECON-5", "Refund Mismatch: refunded amount on Shopify does not match the Razorpay refund total within tolerance."),
    "MATCHED": ("RULE-RECON-7", "Amount Match: order total and captured payment amount agree within tolerance."),
    "PARTIAL_MATCH": ("RULE-RECON-4", "Amount Mismatch / Pending: order total and payment amount differ, or settlement is still pending."),
    "MANUAL_REVIEW": ("RULE-RECON-8", "Ambiguous case flagged for manual review."),
}

_RECOMMENDATIONS = {
    "NOT_APPLICABLE": "No action needed.",
    "DUPLICATE": "Investigate duplicate capture with Razorpay support; refund the extra capture if confirmed.",
    "GHOST_ORDER": "Confirm the order was actually placed and paid; cancel or write off if no payment ever arrives.",
    "MISSING_PAYMENT": "Wait for payment capture; if it does not arrive before the settlement window, this becomes a Ghost Order.",
    "SETTLEMENT_MISMATCH": "Check the Razorpay settlement report for this payment; escalate to Razorpay support if the payment never settles.",
    "REFUND_MISMATCH": "Compare the Shopify refund and Razorpay refund records line by line; issue a correcting refund if Razorpay is short.",
    "MATCHED": "No action needed.",
    "PARTIAL_MATCH": "Review the amount difference; confirm discount/shipping/fee handling matches expectations.",
    "MANUAL_REVIEW": "Requires a human decision; the automated rules could not classify this order confidently.",
}


def _is_razorpay_gateway(payment_gateway_names: list[str]) -> bool:
    """Step 0 gateway eligibility filter."""
    for name in payment_gateway_names:
        lower = name.lower()
        if "razorpay" in lower or "razor" in lower:
            return True
    return False


async def _get_workspace_tolerances(workspace_id: str) -> tuple[float, int]:
    """Return (amount_tolerance, settlement_match_window_days) from workspace_settings."""
    settings_doc = await database.db[database.WORKSPACE_SETTINGS].find_one({"workspace_id": workspace_id})
    amount_tolerance = float((settings_doc or {}).get("reconciliation_amount_tolerance") or 0.0)
    window = int((settings_doc or {}).get("settlement_match_window_days") or 15)
    return amount_tolerance, window


async def _load_shopify_orders(workspace_id: str, date_from, date_to) -> list[dict]:
    """Load Shopify orders for the workspace within the date range."""
    query: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["shopify_created_at"] = range_query
    cursor = database.db[database.SHOPIFY_ORDER].find(query)
    return [doc async for doc in cursor]


async def _load_razorpay_payments(workspace_id: str, date_from, date_to) -> list[dict]:
    """Load Razorpay payments for the workspace within the date range."""
    query: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    cursor = database.db[database.RAZORPAY_PAYMENT].find(query)
    return [doc async for doc in cursor]


async def _load_razorpay_settlements(workspace_id: str, date_from, date_to) -> list[dict]:
    """Load Razorpay settlements for the workspace within the date range."""
    query: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    cursor = database.db[database.RAZORPAY_SETTLEMENT].find(query)
    return [doc async for doc in cursor]


async def _load_razorpay_refunds(workspace_id: str, date_from, date_to) -> list[dict]:
    """Load Razorpay refunds for the workspace within the date range."""
    query: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["razorpay_created_at"] = range_query
    cursor = database.db[database.RAZORPAY_REFUND].find(query)
    return [doc async for doc in cursor]


def _settled_within_window(payment: dict, settlements: list[dict], window_days: int) -> bool:
    """ARCH-AUDIT-004 fix: is THIS payment plausibly covered by a settlement
    that happened within `window_days` of its own capture date?

    This replaces the previous workspace-wide heuristic ("if the workspace
    has any settlement at all, every payment is treated as settled"), which
    meant a payment from long before any settlement existed was marked
    settled just because a settlement happened to exist *today*. Razorpay's
    settlement object does not carry a per-payment breakdown in this
    deployment (that requires the separate Settlement Recon API, which is
    not integrated here), so this is still a heuristic -- but it is now
    anchored to the payment's own timeline instead of being a static,
    workspace-global flag. Documented limitation: a payment can still be
    marked "settled" by a settlement that actually paid out a *different*
    payment captured in the same window; true payment-level certainty
    requires the Settlement Recon API.
    """
    payment_date = payment.get("razorpay_created_at")
    if not payment_date:
        return bool(settlements)
    for settlement in settlements:
        settled_at = settlement.get("settled_at") or settlement.get("razorpay_created_at")
        if not settled_at:
            continue
        if payment_date <= settled_at <= payment_date + timedelta(days=window_days):
            return True
    return False


def _match_status_for_order(
    order: dict,
    payments: list[dict],
    settlements: list[dict],
    refunds: list[dict],
    amount_tolerance: float,
    window_days: int,
) -> dict:
    """Return the full explainable match result for a single order per the
    discrepancy decision table: match_status, reason, confidence, plus the
    Evidence / Business Rule / Calculation / Explanation / Recommendation
    fields the product spec requires on every reconciliation result
    (ARCH-AUDIT-009 fix)."""
    gateway_names = order.get("payment_gateway_names") or []

    def _finish(match_status: str, reason: str, confidence: float, evidence: dict, calculation: str) -> dict:
        rule_id, rule_text = _BUSINESS_RULES[match_status]
        return {
            "match_status": match_status,
            "reason": reason,
            "confidence": confidence,
            "evidence": evidence,
            "business_rule": f"{rule_id}: {rule_text}",
            "calculation": calculation,
            "explanation": reason,
            "recommendation": _RECOMMENDATIONS[match_status],
        }

    if not _is_razorpay_gateway(gateway_names):
        return _finish(
            "NOT_APPLICABLE", "Non-Razorpay gateway", 1.0,
            {"payment_gateway_names": gateway_names}, "No calculation performed (out of scope for this engine).",
        )

    order_id = order.get("shopify_id")
    order_amount = float(order.get("total") or 0.0)
    order_created = order.get("shopify_created_at")
    now = utc_now()

    # Step 3: Duplicate payment detection (before matching).
    captured_payments = [p for p in payments if p.get("status") == "captured"]
    duplicate_payments = [p for p in captured_payments if p.get("order_id") == str(order_id)]
    if len(duplicate_payments) > 1:
        ids = [p.get("razorpay_id") for p in duplicate_payments]
        return _finish(
            "DUPLICATE", "Multiple captured payments for order", 0.9,
            {"shopify_order_id": order_id, "captured_payment_ids": ids},
            f"{len(duplicate_payments)} captured Razorpay payments reference order {order_id}; exactly 1 is expected.",
        )

    matched_payments = duplicate_payments
    if not matched_payments:
        if order_created and (now - order_created).days > window_days:
            return _finish(
                "GHOST_ORDER", "No payment found after settlement window", 0.8,
                {"shopify_order_id": order_id, "order_age_days": (now - order_created).days, "settlement_window_days": window_days},
                f"Order age {(now - order_created).days}d exceeds the {window_days}d settlement window with 0 captured payments found.",
            )
        return _finish(
            "MISSING_PAYMENT", "No captured payment found yet", 0.5,
            {"shopify_order_id": order_id, "order_created_at": order_created.isoformat() if order_created else None},
            "0 captured Razorpay payments found for this order; still within the settlement window.",
        )

    payment = matched_payments[0]
    payment_amount = float(payment.get("amount") or 0.0)

    # Step 4: Settlement gap (per-payment window check, see _settled_within_window).
    if payment.get("captured") and not _settled_within_window(payment, settlements, window_days):
        if order_created and (now - order_created).days > window_days:
            return _finish(
                "SETTLEMENT_MISMATCH", "Captured payment with no settlement within the window", 0.7,
                {"razorpay_payment_id": payment.get("razorpay_id"), "payment_captured_at": payment.get("razorpay_created_at").isoformat() if payment.get("razorpay_created_at") else None, "settlement_window_days": window_days},
                f"No settlement found within {window_days}d of payment capture ({payment.get('razorpay_id')}).",
            )
        return _finish(
            "PARTIAL_MATCH", "Payment captured, settlement pending", 0.6,
            {"razorpay_payment_id": payment.get("razorpay_id"), "settlement_window_days": window_days},
            f"Payment captured; still within the {window_days}d settlement window, no settlement match yet.",
        )

    # Step 5: Refund mismatch.
    if order.get("financial_status") == "refunded":
        shopify_refund_total = sum(float(r.get("amount") or 0.0) for r in refunds)
        difference = abs(shopify_refund_total - payment_amount)
        if difference > amount_tolerance:
            return _finish(
                "REFUND_MISMATCH", "Refund amount does not match payment", 0.8,
                {"razorpay_refund_total": shopify_refund_total, "payment_amount": payment_amount, "tolerance": amount_tolerance},
                f"|{shopify_refund_total} - {payment_amount}| = {difference} > tolerance {amount_tolerance}.",
            )

    amount_difference = abs(order_amount - payment_amount)
    if amount_difference <= amount_tolerance:
        return _finish(
            "MATCHED", "Exact amount match", 0.95,
            {"order_amount": order_amount, "payment_amount": payment_amount, "tolerance": amount_tolerance},
            f"|{order_amount} - {payment_amount}| = {amount_difference} <= tolerance {amount_tolerance}.",
        )
    return _finish(
        "PARTIAL_MATCH", "Amount within tolerance band but not exact", 0.7,
        {"order_amount": order_amount, "payment_amount": payment_amount, "tolerance": amount_tolerance},
        f"|{order_amount} - {payment_amount}| = {amount_difference} > tolerance {amount_tolerance}.",
    )


async def run_reconciliation(context: AuthContext, date_from, date_to, request: Request) -> dict:
    """Run reconciliation for the workspace within the date range."""
    workspace_id = context.workspace_id
    idempotency_key = f"recon:{workspace_id}:{date_from.isoformat() if date_from else 'all'}:{date_to.isoformat() if date_to else 'all'}"
    existing = await database.db[database.RECONCILIATION_JOB].find_one({"idempotency_key": idempotency_key})
    if existing:
        return {"job_id": existing["_id"], "status": existing["status"]}

    now = utc_now()
    job_id = new_id()
    job = {
        "_id": job_id,
        "workspace_id": workspace_id,
        "status": "RUNNING",
        "started_at": now,
        "completed_at": None,
        "error": None,
        "counts": {},
        "idempotency_key": idempotency_key,
        "date_from": date_from,
        "date_to": date_to,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    await database.db[database.RECONCILIATION_JOB].insert_one(job)
    await audit.record(
        action="RECONCILIATION_STARTED",
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="RECONCILIATION_JOB",
        resource_id=job_id,
        request=request,
        metadata={"date_from": date_from.isoformat() if date_from else None, "date_to": date_to.isoformat() if date_to else None},
    )

    counts = {
        "total": 0,
        "matched": 0,
        "partial_match": 0,
        "unmatched": 0,
        "missing_payment": 0,
        "ghost_order": 0,
        "duplicate_payment": 0,
        "refund_mismatch": 0,
        "settlement_mismatch": 0,
        "manual_review": 0,
        "not_applicable": 0,
    }

    try:
        shopify_orders = await _load_shopify_orders(workspace_id, date_from, date_to)
        razorpay_payments = await _load_razorpay_payments(workspace_id, date_from, date_to)
        razorpay_settlements = await _load_razorpay_settlements(workspace_id, date_from, date_to)
        razorpay_refunds = await _load_razorpay_refunds(workspace_id, date_from, date_to)
        amount_tolerance, window_days = await _get_workspace_tolerances(workspace_id)

        for order in shopify_orders:
            match = _match_status_for_order(
                order, razorpay_payments, razorpay_settlements, razorpay_refunds, amount_tolerance, window_days
            )
            match_status, reason, confidence = match["match_status"], match["reason"], match["confidence"]
            counts["total"] += 1
            counts[match_status.lower()] = counts.get(match_status.lower(), 0) + 1

            result = {
                "_id": new_id(),
                "workspace_id": workspace_id,
                "job_id": job_id,
                "match_status": match_status,
                "shopify_order_id": order.get("shopify_id"),
                "razorpay_order_id": None,
                "shopify_payment_ids": [],
                "razorpay_payment_ids": [],
                "shopify_refund_ids": [],
                "razorpay_refund_ids": [],
                "shopify_settlement_ids": [],
                "razorpay_settlement_ids": [],
                "amount_shopify": float(order.get("total") or 0.0),
                "amount_razorpay": 0.0,
                "amount_difference": 0.0,
                "currency": order.get("currency"),
                "confidence": confidence,
                "reason": reason,
                # ARCH-AUDIT-009 fix: the spec requires Evidence, Business Rule,
                # Calculation, Explanation and Recommendation on every result.
                "evidence": match["evidence"],
                "business_rule": match["business_rule"],
                "calculation": match["calculation"],
                "explanation": match["explanation"],
                "recommendation": match["recommendation"],
                "raw": {},
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
            await database.db[database.RECONCILIATION_RESULT].insert_one(result)

            if match_status in ("GHOST_ORDER", "MISSING_PAYMENT", "DUPLICATE", "SETTLEMENT_MISMATCH", "REFUND_MISMATCH", "MANUAL_REVIEW"):
                exception = {
                    "_id": new_id(),
                    "workspace_id": workspace_id,
                    "job_id": job_id,
                    "result_id": result["_id"],
                    "exception_type": match_status,
                    "severity": "CRITICAL" if match_status in ("GHOST_ORDER", "MISSING_PAYMENT", "DUPLICATE") else "WARNING",
                    "status": "OPEN",
                    "shopify_order_id": order.get("shopify_id"),
                    "amount": float(order.get("total") or 0.0),
                    "currency": order.get("currency"),
                    "root_cause": reason,
                    # ARCH-AUDIT-009 fix: rule-specific recommendation instead
                    # of a single hardcoded "Review manually" for every type.
                    "suggested_action": match["recommendation"],
                    "created_at": now,
                    "updated_at": now,
                    "deleted_at": None,
                }
                await database.db[database.RECONCILIATION_EXCEPTION].insert_one(exception)

        status = "COMPLETED"
        error = None
    except AppError as exc:
        status = "FAILED"
        error = exc.code
        counts = counts or {}

    await database.db[database.RECONCILIATION_JOB].update_one(
        {"_id": job_id},
        {"$set": {"status": status, "completed_at": utc_now(), "error": error, "counts": counts, "updated_at": now}},
    )
    await audit.record(
        action="RECONCILIATION_COMPLETED" if status == "COMPLETED" else "RECONCILIATION_FAILED",
        actor_user_id=context.user_id,
        workspace_id=workspace_id,
        resource_type="RECONCILIATION_JOB",
        resource_id=job_id,
        request=request,
        metadata={"counts": counts, "error": error},
    )
    return {"job_id": job_id, "status": status, "counts": counts}


async def list_reconciliation_results(context: AuthContext, page_request, match_status: str | None, date_from, date_to) -> dict:
    """List reconciliation results with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if match_status:
        query["match_status"] = match_status
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["created_at"] = range_query
    total = await database.db[database.RECONCILIATION_RESULT].count_documents(query)
    cursor = (
        database.db[database.RECONCILIATION_RESULT]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "amount_shopify"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = []
    async for doc in cursor:
        items.append(
            {
                "id": doc["_id"],
                "workspace_id": doc["workspace_id"],
                "job_id": doc["job_id"],
                "match_status": doc["match_status"],
                "shopify_order_id": doc.get("shopify_order_id"),
                "razorpay_order_id": doc.get("razorpay_order_id"),
                "shopify_payment_ids": doc.get("shopify_payment_ids", []),
                "razorpay_payment_ids": doc.get("razorpay_payment_ids", []),
                "shopify_refund_ids": doc.get("shopify_refund_ids", []),
                "razorpay_refund_ids": doc.get("razorpay_refund_ids", []),
                "shopify_settlement_ids": doc.get("shopify_settlement_ids", []),
                "razorpay_settlement_ids": doc.get("razorpay_settlement_ids", []),
                "amount_shopify": doc.get("amount_shopify", 0.0),
                "amount_razorpay": doc.get("amount_razorpay", 0.0),
                "amount_difference": doc.get("amount_difference", 0.0),
                "currency": doc.get("currency"),
                "confidence": doc.get("confidence", 0.0),
                "reason": doc.get("reason"),
                "evidence": doc.get("evidence"),
                "business_rule": doc.get("business_rule"),
                "calculation": doc.get("calculation"),
                "explanation": doc.get("explanation"),
                "recommendation": doc.get("recommendation"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
            }
        )
    return page_response(items, total, page_request)


async def list_reconciliation_exceptions(context: AuthContext, page_request, status: str | None, exception_type: str | None) -> dict:
    """List reconciliation exceptions with pagination and filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if status:
        query["status"] = status
    if exception_type:
        query["exception_type"] = exception_type
    total = await database.db[database.RECONCILIATION_EXCEPTION].count_documents(query)
    cursor = (
        database.db[database.RECONCILIATION_EXCEPTION]
        .find(query)
        .sort(page_request.sort_spec({"created_at", "updated_at", "amount"}))
        .skip(page_request.skip)
        .limit(page_request.size)
    )
    items = []
    async for doc in cursor:
        items.append(
            {
                "id": doc["_id"],
                "workspace_id": doc["workspace_id"],
                "job_id": doc["job_id"],
                "result_id": doc.get("result_id"),
                "exception_type": doc["exception_type"],
                "severity": doc["severity"],
                "status": doc["status"],
                "shopify_order_id": doc.get("shopify_order_id"),
                "razorpay_order_id": doc.get("razorpay_order_id"),
                "payment_id": doc.get("payment_id"),
                "settlement_id": doc.get("settlement_id"),
                "amount": doc.get("amount", 0.0),
                "currency": doc.get("currency"),
                "root_cause": doc.get("root_cause"),
                "suggested_action": doc.get("suggested_action"),
                "resolved_at": doc.get("resolved_at"),
                "resolved_by": doc.get("resolved_by"),
                "resolution_note": doc.get("resolution_note"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
            }
        )
    return page_response(items, total, page_request)


async def get_reconciliation_summary(context: AuthContext, date_from, date_to) -> dict:
    """Return a summary of reconciliation results for the workspace."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["created_at"] = range_query

    total = await database.db[database.RECONCILIATION_RESULT].count_documents(query)
    matched = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "MATCHED"})
    partial = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "PARTIAL_MATCH"})
    unmatched = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "UNMATCHED"})
    missing_payment = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "MISSING_PAYMENT"})
    ghost_order = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "GHOST_ORDER"})
    duplicate_payment = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "DUPLICATE"})
    refund_mismatch = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "REFUND_MISMATCH"})
    settlement_mismatch = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "SETTLEMENT_MISMATCH"})
    manual_review = await database.db[database.RECONCILIATION_RESULT].count_documents({**query, "match_status": "MANUAL_REVIEW"})

    match_rate = (matched + partial) / total if total > 0 else 0.0
    confidence_score = 0.0  # Could be computed from average confidence of matched results.

    return {
        "total_orders": total,
        "matched": matched,
        "partial_match": partial,
        "unmatched": unmatched,
        "missing_payment": missing_payment,
        "ghost_order": ghost_order,
        "duplicate_payment": duplicate_payment,
        "refund_mismatch": refund_mismatch,
        "settlement_mismatch": settlement_mismatch,
        "manual_review": manual_review,
        "match_rate": match_rate,
        "confidence_score": confidence_score,
    }


# --- Milestone 5: Dashboard & Analytics ---


async def _dashboard_date_filter(date_from, date_to):
    """Build a MongoDB date filter for dashboard aggregations."""
    query: dict = {}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["created_at"] = range_query
    return query


async def _sum_field(collection: str, workspace_id: str, date_query: dict, field: str = "amount") -> float:
    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {"$group": {"_id": None, "total": {"$sum": f"${field}"}}},
    ]
    total = 0.0
    async for doc in database.db[collection].aggregate(pipeline):
        total = float(doc.get("total") or 0.0)
    return total


async def get_money_at_risk(context: AuthContext, date_from, date_to) -> dict:
    """ARCH-AUDIT-007 fix: 'Money At Risk' -- the amount tied up in OPEN
    reconciliation exceptions (ghost orders, missing payments, duplicates,
    settlement/refund mismatches) that has not yet been resolved. This is one
    of the seven financial detection rules required by the product spec and
    previously had no implementation anywhere in the codebase.
    """
    workspace_id = context.workspace_id
    query: dict = {"workspace_id": workspace_id, "deleted_at": None, "status": "OPEN"}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        query["created_at"] = range_query

    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$exception_type", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    by_type: dict[str, dict] = {}
    total_at_risk = 0.0
    async for doc in database.db[database.RECONCILIATION_EXCEPTION].aggregate(pipeline):
        amount = float(doc.get("total") or 0.0)
        by_type[doc["_id"] or "UNKNOWN"] = {"amount": amount, "count": doc.get("count", 0)}
        total_at_risk += amount

    currency_doc = await database.db[database.RECONCILIATION_EXCEPTION].find_one(query, sort=[("created_at", -1)])
    currency = (currency_doc or {}).get("currency")

    return {
        "total_amount": total_at_risk,
        "currency": currency,
        "open_exception_count": sum(v["count"] for v in by_type.values()),
        "by_exception_type": by_type,
    }


async def get_dashboard_overview(context: AuthContext, date_from, date_to) -> dict:
    """Return the dashboard overview cards.

    ARCH-AUDIT-013 fix: the 13 independent aggregate/count queries this card
    needs are now issued concurrently with asyncio.gather instead of one at a
    time, so overview latency is bounded by the slowest single query rather
    than the sum of all of them.
    """
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    recon_query: dict = {"workspace_id": workspace_id, "deleted_at": None}
    if date_from or date_to:
        range_query: dict = {}
        if date_from:
            range_query["$gte"] = date_from
        if date_to:
            range_query["$lte"] = date_to
        recon_query["created_at"] = range_query

    (
        revenue,
        total_orders,
        total_payments,
        total_refunds,
        total_settlements,
        total_recon,
        matched_recon,
        partial_recon,
        total_exceptions,
        critical_exceptions,
        pending_exceptions,
        shopify_conn,
        razorpay_conn,
        money_at_risk,
    ) = await asyncio.gather(
        _sum_field(database.SHOPIFY_ORDER, workspace_id, date_query, "total"),
        database.db[database.SHOPIFY_ORDER].count_documents({"workspace_id": workspace_id, "deleted_at": None, **date_query}),
        _sum_field(database.RAZORPAY_PAYMENT, workspace_id, date_query, "amount"),
        _sum_field(database.RAZORPAY_REFUND, workspace_id, date_query, "amount"),
        _sum_field(database.RAZORPAY_SETTLEMENT, workspace_id, date_query, "amount"),
        database.db[database.RECONCILIATION_RESULT].count_documents(recon_query),
        database.db[database.RECONCILIATION_RESULT].count_documents({**recon_query, "match_status": "MATCHED"}),
        database.db[database.RECONCILIATION_RESULT].count_documents({**recon_query, "match_status": "PARTIAL_MATCH"}),
        database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None}),
        database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None, "severity": "CRITICAL"}),
        database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None, "status": "OPEN"}),
        database.db[database.SHOPIFY_CONNECTION].count_documents({"workspace_id": workspace_id, "status": "ACTIVE"}),
        database.db[database.RAZORPAY_CONNECTION].count_documents({"workspace_id": workspace_id, "status": "ACTIVE"}),
        get_money_at_risk(context, date_from, date_to),
    )
    match_rate = (matched_recon + partial_recon) / total_recon if total_recon > 0 else 0.0
    connected_integrations = shopify_conn + razorpay_conn

    return {
        "revenue": revenue,
        "total_orders": total_orders,
        "total_payments": total_payments,
        "total_refunds": total_refunds,
        "total_settlements": total_settlements,
        "reconciliation_match_rate": match_rate,
        "total_exceptions": total_exceptions,
        "critical_exceptions": critical_exceptions,
        "pending_exceptions": pending_exceptions,
        "connected_integrations": connected_integrations,
        "money_at_risk": money_at_risk["total_amount"],
    }


async def get_dashboard_revenue(context: AuthContext, date_from, date_to) -> dict:
    """Return revenue overview with daily/weekly/monthly trends."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    # Total revenue.
    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]
    cursor = database.db[database.SHOPIFY_ORDER].aggregate(pipeline)
    total = 0.0
    async for doc in cursor:
        total = float(doc.get("total") or 0.0)

    # Daily trend (last 30 days or date range).
    daily_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$shopify_created_at"}},
                "total": {"$sum": "$total"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily = []
    async for doc in database.db[database.SHOPIFY_ORDER].aggregate(daily_pipeline):
        daily.append({"date": doc["_id"], "total": float(doc.get("total") or 0.0)})

    # Weekly trend.
    weekly_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%U", "date": "$shopify_created_at"}},
                "total": {"$sum": "$total"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    weekly = []
    async for doc in database.db[database.SHOPIFY_ORDER].aggregate(weekly_pipeline):
        weekly.append({"week": doc["_id"], "total": float(doc.get("total") or 0.0)})

    # Monthly trend.
    monthly_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$shopify_created_at"}},
                "total": {"$sum": "$total"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    monthly = []
    async for doc in database.db[database.SHOPIFY_ORDER].aggregate(monthly_pipeline):
        monthly.append({"month": doc["_id"], "total": float(doc.get("total") or 0.0)})

    return {"total": total, "daily": daily, "weekly": weekly, "monthly": monthly}


async def get_dashboard_orders(context: AuthContext, date_from, date_to) -> dict:
    """Return orders count with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)
    total = await database.db[database.SHOPIFY_ORDER].count_documents({"workspace_id": workspace_id, "deleted_at": None, **date_query})

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$shopify_created_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.SHOPIFY_ORDER].aggregate(pipeline):
        trend.append({"date": doc["_id"], "count": doc.get("count", 0)})
    return {"total": total, "trend": trend}


async def get_dashboard_payments(context: AuthContext, date_from, date_to) -> dict:
    """Return payments total with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    cursor = database.db[database.RAZORPAY_PAYMENT].aggregate(pipeline)
    total = 0.0
    async for doc in cursor:
        total = float(doc.get("total") or 0.0)

    trend_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$razorpay_created_at"}},
                "total": {"$sum": "$amount"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.RAZORPAY_PAYMENT].aggregate(trend_pipeline):
        trend.append({"date": doc["_id"], "total": float(doc.get("total") or 0.0)})
    return {"total": total, "trend": trend}


async def get_dashboard_refunds(context: AuthContext, date_from, date_to) -> dict:
    """Return refunds total with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    cursor = database.db[database.RAZORPAY_REFUND].aggregate(pipeline)
    total = 0.0
    async for doc in cursor:
        total = float(doc.get("total") or 0.0)

    trend_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$razorpay_created_at"}},
                "total": {"$sum": "$amount"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.RAZORPAY_REFUND].aggregate(trend_pipeline):
        trend.append({"date": doc["_id"], "total": float(doc.get("total") or 0.0)})
    return {"total": total, "trend": trend}


async def get_dashboard_settlements(context: AuthContext, date_from, date_to) -> dict:
    """Return settlements total with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    cursor = database.db[database.RAZORPAY_SETTLEMENT].aggregate(pipeline)
    total = 0.0
    async for doc in cursor:
        total = float(doc.get("total") or 0.0)

    trend_pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$razorpay_created_at"}},
                "total": {"$sum": "$amount"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.RAZORPAY_SETTLEMENT].aggregate(trend_pipeline):
        trend.append({"date": doc["_id"], "total": float(doc.get("total") or 0.0)})
    return {"total": total, "trend": trend}


async def get_dashboard_exceptions(context: AuthContext, date_from, date_to) -> dict:
    """Return exception counts with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    total = await database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None, **date_query})
    critical = await database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None, "severity": "CRITICAL", **date_query})
    pending = await database.db[database.RECONCILIATION_EXCEPTION].count_documents({"workspace_id": workspace_id, "deleted_at": None, "status": "OPEN", **date_query})

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.RECONCILIATION_EXCEPTION].aggregate(pipeline):
        trend.append({"date": doc["_id"], "count": doc.get("count", 0)})
    return {"total": total, "critical": critical, "pending": pending, "trend": trend}


async def get_dashboard_match_rate(context: AuthContext, date_from, date_to) -> dict:
    """Return match rate with daily trend."""
    workspace_id = context.workspace_id
    date_query = await _dashboard_date_filter(date_from, date_to)

    total = await database.db[database.RECONCILIATION_RESULT].count_documents({"workspace_id": workspace_id, "deleted_at": None, **date_query})
    matched = await database.db[database.RECONCILIATION_RESULT].count_documents({**date_query, "workspace_id": workspace_id, "deleted_at": None, "match_status": "MATCHED"})
    partial = await database.db[database.RECONCILIATION_RESULT].count_documents({**date_query, "workspace_id": workspace_id, "deleted_at": None, "match_status": "PARTIAL_MATCH"})
    rate = (matched + partial) / total if total > 0 else 0.0

    pipeline = [
        {"$match": {"workspace_id": workspace_id, "deleted_at": None, **date_query}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "total": {"$sum": 1},
                "matched": {"$sum": {"$cond": [{"$eq": ["$match_status", "MATCHED"]}, 1, 0]}},
                "partial": {"$sum": {"$cond": [{"$eq": ["$match_status", "PARTIAL_MATCH"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    trend = []
    async for doc in database.db[database.RECONCILIATION_RESULT].aggregate(pipeline):
        doc_total = doc.get("total", 1)
        doc_rate = (doc.get("matched", 0) + doc.get("partial", 0)) / doc_total if doc_total > 0 else 0.0
        trend.append({"date": doc["_id"], "rate": doc_rate})
    return {"rate": rate, "trend": trend}


async def get_dashboard_analytics(context: AuthContext, date_from, date_to) -> dict:
    """Return the full analytics payload."""
    revenue = await get_dashboard_revenue(context, date_from, date_to)
    orders = await get_dashboard_orders(context, date_from, date_to)
    payments = await get_dashboard_payments(context, date_from, date_to)
    refunds = await get_dashboard_refunds(context, date_from, date_to)
    settlements = await get_dashboard_settlements(context, date_from, date_to)
    exceptions = await get_dashboard_exceptions(context, date_from, date_to)
    match_rate = await get_dashboard_match_rate(context, date_from, date_to)
    return {
        "revenue": revenue,
        "orders": orders,
        "payments": payments,
        "refunds": refunds,
        "settlements": settlements,
        "exceptions": exceptions,
        "match_rate": match_rate,
    }


# --- Milestone 6: Production Readiness ---


async def _build_export_query(context: AuthContext, export_request: ExportRequest) -> dict:
    """Build a MongoDB query for export based on filters."""
    query: dict = {"workspace_id": context.workspace_id, "deleted_at": None}
    if export_request.date_from or export_request.date_to:
        range_query: dict = {}
        if export_request.date_from:
            range_query["$gte"] = export_request.date_from
        if export_request.date_to:
            range_query["$lte"] = export_request.date_to
        query["created_at"] = range_query
    if export_request.status:
        query["status"] = export_request.status
    if export_request.match_status:
        query["match_status"] = export_request.match_status
    if export_request.exception_type:
        query["exception_type"] = export_request.exception_type
    if export_request.severity:
        query["severity"] = export_request.severity
    if export_request.payment_id:
        query["razorpay_id"] = export_request.payment_id
    if export_request.order_id:
        query["shopify_order_id"] = int(export_request.order_id) if export_request.order_id.isdigit() else None
    if export_request.shop_domain:
        connection = await database.db[database.SHOPIFY_CONNECTION].find_one(
            {"workspace_id": context.workspace_id, "shop_domain": export_request.shop_domain}
        )
        if connection:
            query["workspace_id"] = context.workspace_id
        else:
            query["workspace_id"] = None  # No results
    return query


EXPORT_FORMATS = {"csv", "excel", "pdf"}
_EXPORT_TTL_HOURS = 24
_EXPORT_PDF_ROW_LIMIT = 2000  # keep generated PDFs a readable/reasonable size
_EXPORT_FILE_EXTENSION = {"csv": "csv", "excel": "xlsx", "pdf": "pdf"}


def _export_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return value


def _export_row(doc: dict, columns: list[str]) -> dict:
    return {c: _export_value(doc.get(c)) for c in columns}


def _write_export_csv(rows: list[dict], columns: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _write_export_xlsx(rows: list[dict], columns: list[str]) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(c, "") for c in columns])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _write_export_pdf(rows: list[dict], columns: list[str], title: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    truncated = len(rows) > _EXPORT_PDF_ROW_LIMIT
    pdf_rows = rows[:_EXPORT_PDF_ROW_LIMIT]
    table_data = [columns] + [[str(row.get(c, "")) for c in columns] for row in pdf_rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
            ]
        )
    )
    elements.append(table)
    if truncated:
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(
                f"Showing the first {_EXPORT_PDF_ROW_LIMIT} of {len(rows)} rows. "
                "Use the CSV or Excel export for the complete data set.",
                styles["Normal"],
            )
        )
    doc.build(elements)
    return buffer.getvalue()


async def _finalize_export(
    context: AuthContext, base_name: str, fmt: str, docs: list[dict], columns: list[str], title: str
) -> dict:
    """ARCH-AUDIT-002 fix: actually generate the requested file and persist it
    (short-lived, workspace-scoped) so the returned download_url resolves to
    a real file via GET /exports/download/{filename} instead of a URL that
    was never backed by anything.
    """
    if fmt not in EXPORT_FORMATS:
        raise AppError(
            "VALIDATION-001",
            details=[{"field": "format", "issue": f"Unsupported export format '{fmt}'. Supported: csv, xlsx, pdf."}],
        )

    rows = [_export_row(doc, columns) for doc in docs]
    if fmt == "csv":
        content = _write_export_csv(rows, columns)
        content_type = "text/csv"
    elif fmt == "excel":
        content = _write_export_xlsx(rows, columns)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = _write_export_pdf(rows, columns, title)
        content_type = "application/pdf"

    file_id = new_id()
    filename = f"{base_name}_{file_id}.{_EXPORT_FILE_EXTENSION[fmt]}"
    now = utc_now()
    file_doc = {
        "_id": file_id,
        "workspace_id": context.workspace_id,
        "filename": filename,
        "format": fmt,
        "content_type": content_type,
        "data": Binary(content),
        "record_count": len(rows),
        "created_at": now,
        "expires_at": now + timedelta(hours=_EXPORT_TTL_HOURS),
    }
    await database.db[database.EXPORT_FILE].insert_one(file_doc)

    return {
        "download_url": f"/api/v1/exports/download/{filename}",
        "filename": filename,
        "format": fmt,
        "record_count": len(rows),
    }


async def download_export(context: AuthContext, filename: str) -> tuple[bytes, str, str]:
    """Return (content, content_type, filename) for a previously generated
    export, enforcing workspace ownership (ARCH-AUDIT-002 fix)."""
    doc = await database.db[database.EXPORT_FILE].find_one({"filename": filename})
    if not doc or doc["workspace_id"] != context.workspace_id:
        raise AppError("EXPORT-001")
    return bytes(doc["data"]), doc["content_type"], doc["filename"]


async def export_reconciliation_results(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export reconciliation results as CSV/Excel/PDF."""
    query = await _build_export_query(context, export_request)
    cursor = database.db[database.RECONCILIATION_RESULT].find(query).sort("created_at", -1)
    results = [doc async for doc in cursor]
    columns = [
        "shopify_order_id", "match_status", "amount_shopify", "amount_razorpay",
        "amount_difference", "currency", "confidence", "business_rule", "explanation",
        "recommendation", "created_at",
    ]
    return await _finalize_export(context, "reconciliation_results", export_request.format, results, columns, "Reconciliation Results")


async def export_exceptions(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export reconciliation exceptions as CSV/Excel/PDF."""
    query = await _build_export_query(context, export_request)
    cursor = database.db[database.RECONCILIATION_EXCEPTION].find(query).sort("created_at", -1)
    exceptions = [doc async for doc in cursor]
    columns = [
        "shopify_order_id", "exception_type", "severity", "status", "amount", "currency",
        "root_cause", "suggested_action", "created_at",
    ]
    return await _finalize_export(context, "exceptions", export_request.format, exceptions, columns, "Reconciliation Exceptions")


async def export_dashboard_summary(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export dashboard summary as CSV/Excel/PDF."""
    overview = await get_dashboard_overview(context, export_request.date_from, export_request.date_to)
    columns = list(overview.keys())
    return await _finalize_export(context, "dashboard_summary", export_request.format, [overview], columns, "Dashboard Summary")


async def export_payments(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export payments as CSV/Excel/PDF."""
    query = await _build_export_query(context, export_request)
    cursor = database.db[database.RAZORPAY_PAYMENT].find(query).sort("razorpay_created_at", -1)
    payments = [doc async for doc in cursor]
    columns = [
        "razorpay_id", "order_id", "amount", "currency", "status", "method", "fee", "tax",
        "captured", "refunded", "razorpay_created_at",
    ]
    return await _finalize_export(context, "payments", export_request.format, payments, columns, "Razorpay Payments")


async def export_refunds(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export refunds as CSV/Excel/PDF."""
    query = await _build_export_query(context, export_request)
    cursor = database.db[database.RAZORPAY_REFUND].find(query).sort("razorpay_created_at", -1)
    refunds = [doc async for doc in cursor]
    columns = ["razorpay_id", "payment_id", "amount", "currency", "status", "reason", "razorpay_created_at"]
    return await _finalize_export(context, "refunds", export_request.format, refunds, columns, "Razorpay Refunds")


async def export_settlements(context: AuthContext, export_request: ExportRequest) -> dict:
    """Export settlements as CSV/Excel/PDF."""
    query = await _build_export_query(context, export_request)
    cursor = database.db[database.RAZORPAY_SETTLEMENT].find(query).sort("razorpay_created_at", -1)
    settlements = [doc async for doc in cursor]
    columns = ["razorpay_id", "amount", "currency", "status", "fee", "tax", "settled_at", "razorpay_created_at"]
    return await _finalize_export(context, "settlements", export_request.format, settlements, columns, "Razorpay Settlements")


async def get_notification_preferences(context: AuthContext) -> dict:
    """Get notification preferences for the workspace."""
    prefs = await database.db[database.WORKSPACE_SETTINGS].find_one({"workspace_id": context.workspace_id})
    if not prefs:
        return {
            "critical_reconciliation_failures": True,
            "failed_shopify_sync": True,
            "failed_razorpay_sync": True,
            "oauth_expiration": True,
            "webhook_failures": True,
            "email_enabled": False,
            "webhook_url": None,
        }
    return {
        "id": prefs["_id"],
        "workspace_id": prefs["workspace_id"],
        "critical_reconciliation_failures": prefs.get("notification_settings", {}).get("critical_reconciliation_failures", True),
        "failed_shopify_sync": prefs.get("notification_settings", {}).get("failed_shopify_sync", True),
        "failed_razorpay_sync": prefs.get("notification_settings", {}).get("failed_razorpay_sync", True),
        "oauth_expiration": prefs.get("notification_settings", {}).get("oauth_expiration", True),
        "webhook_failures": prefs.get("notification_settings", {}).get("webhook_failures", True),
        "email_enabled": prefs.get("notification_settings", {}).get("email_enabled", False),
        "webhook_url": prefs.get("notification_settings", {}).get("webhook_url"),
        "created_at": prefs["created_at"],
        "updated_at": prefs["updated_at"],
    }


async def update_notification_preferences(context: AuthContext, update_data: NotificationPreferenceUpdate) -> dict:
    """Update notification preferences for the workspace."""
    settings_doc = await database.db[database.WORKSPACE_SETTINGS].find_one({"workspace_id": context.workspace_id})
    if not settings_doc:
        raise AppError("WORKSPACE-001")
    
    notification_settings = settings_doc.get("notification_settings", {})
    if update_data.critical_reconciliation_failures is not None:
        notification_settings["critical_reconciliation_failures"] = update_data.critical_reconciliation_failures
    if update_data.failed_shopify_sync is not None:
        notification_settings["failed_shopify_sync"] = update_data.failed_shopify_sync
    if update_data.failed_razorpay_sync is not None:
        notification_settings["failed_razorpay_sync"] = update_data.failed_razorpay_sync
    if update_data.oauth_expiration is not None:
        notification_settings["oauth_expiration"] = update_data.oauth_expiration
    if update_data.webhook_failures is not None:
        notification_settings["webhook_failures"] = update_data.webhook_failures
    if update_data.email_enabled is not None:
        notification_settings["email_enabled"] = update_data.email_enabled
    if update_data.webhook_url is not None:
        notification_settings["webhook_url"] = update_data.webhook_url
    
    await database.db[database.WORKSPACE_SETTINGS].update_one(
        {"workspace_id": context.workspace_id},
        {"$set": {"notification_settings": notification_settings, "updated_at": utc_now()}},
    )
    
    return await get_notification_preferences(context)


async def send_notification(context: AuthContext, notification_type: str, payload: dict) -> dict:
    """Send a notification based on workspace preferences.

    ARCH-AUDIT-003 fix: this previously only logged via `logger.info` and
    always reported success regardless of whether anything was actually
    delivered. It now really sends:
      - email, via the existing SMTP-backed email service, to the
        workspace owner's registered address, when email_enabled is set;
      - webhook, via an HTTP POST to the configured webhook_url, when set.
    Every attempt (success or failure) is recorded in
    notification_delivery_log so failures are visible/auditable rather than
    silently swallowed. If neither channel is configured, this returns a
    clearly-labeled "skipped" result -- it never claims delivery that did
    not happen.
    """
    prefs = await get_notification_preferences(context)

    enabled = prefs.get(notification_type, False)
    if not enabled:
        return {"status": "skipped", "reason": "notification_type_disabled"}

    workspace = await database.db[database.WORKSPACE].find_one({"_id": context.workspace_id})
    workspace_name = (workspace or {}).get("name") or context.workspace_id
    title = payload.get("title") or notification_type.replace("_", " ").title()
    message = payload.get("message") or f"A {notification_type.replace('_', ' ')} event occurred."

    results: dict = {}

    if prefs.get("email_enabled"):
        owner_email = None
        if workspace and workspace.get("owner_id"):
            owner = await database.db[database.USER].find_one({"_id": workspace["owner_id"]})
            owner_email = (owner or {}).get("email")
        if not owner_email:
            results["email"] = {"status": "FAILED", "error": "NO_RECIPIENT"}
        else:
            email_result = await email_service.send(
                "WORKSPACE_NOTIFICATION",
                owner_email,
                notification_title=title,
                message=message,
                workspace_name=workspace_name,
                notification_type=notification_type,
            )
            results["email"] = email_result

    webhook_url = prefs.get("webhook_url")
    if webhook_url:
        webhook_body = {
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "workspace_id": context.workspace_id,
            "payload": payload,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=webhook_body)
            if 200 <= response.status_code < 300:
                results["webhook"] = {"status": "SENT", "error": None}
            else:
                results["webhook"] = {"status": "FAILED", "error": f"HTTP_{response.status_code}"}
        except httpx.HTTPError as exc:
            results["webhook"] = {"status": "FAILED", "error": type(exc).__name__}

    if not results:
        # Enabled in preferences but no delivery channel is actually
        # configured (no email_enabled, no webhook_url) -- fail gracefully
        # and say so, rather than reporting a fake "sent".
        return {"status": "skipped", "reason": "no_delivery_channel_configured", "type": notification_type}

    now = utc_now()
    await database.db[database.NOTIFICATION_DELIVERY_LOG].insert_one(
        {
            "_id": new_id(),
            "workspace_id": context.workspace_id,
            "notification_type": notification_type,
            "channels": results,
            "created_at": now,
            "updated_at": now,
        }
    )

    overall = "failed"
    statuses = {r.get("status") for r in results.values()}
    if "SENT" in statuses:
        overall = "sent"
    elif "PENDING_NO_TRANSPORT" in statuses:
        # Honest, not a fake success: recorded/queued but no SMTP is
        # configured on this deployment, so nothing actually left the server.
        overall = "pending_no_transport"
    return {"status": overall, "type": notification_type, "channels": results}


async def get_health_status() -> dict:
    """Get overall health status."""
    now = utc_now()
    
    # Database health
    db_start = now
    try:
        await database.db.command("ping")
        db_latency = (utc_now() - db_start).total_seconds() * 1000
        db_status = "healthy"
        collections = len(await database.db.list_collection_names())
    except Exception as exc:
        db_latency = 0.0
        db_status = f"unhealthy: {exc}"
        collections = 0
    
    # Integrations health
    integrations = {
        "shopify": {
            "status": "configured" if settings.shopify_configured else "not_configured",
            "configured": settings.shopify_configured,
        },
        "razorpay": {
            "status": "configured" if settings.razorpay_configured else "not_configured",
            "configured": settings.razorpay_configured,
        },
    }
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "timestamp": now,
        "database": {
            "status": db_status,
            "latency_ms": db_latency,
            "collections": collections,
        },
        "integrations": integrations,
    }


async def get_database_health() -> dict:
    """Get detailed database health."""
    now = utc_now()
    start = now
    try:
        await database.db.command("ping")
        latency = (utc_now() - start).total_seconds() * 1000
        collections = len(await database.db.list_collection_names())
        return {
            "status": "healthy",
            "latency_ms": latency,
            "collections": collections,
        }
    except Exception as exc:
        return {
            "status": f"unhealthy: {exc}",
            "latency_ms": 0.0,
            "collections": 0,
        }


async def get_integration_health(integration: str) -> dict:
    """Get health status for a specific integration."""
    now = utc_now()
    
    if integration == "shopify":
        configured = settings.shopify_configured
        status = "configured" if configured else "not_configured"
        error = None if configured else "SHOPIFY_API_KEY not set"
    elif integration == "razorpay":
        configured = settings.razorpay_configured
        status = "configured" if configured else "not_configured"
        error = None if configured else "RAZORPAY_KEY_ID not set"
    elif integration == "reconciliation":
        # Reconciliation is always available (no external service)
        return {
            "status": "available",
            "configured": True,
            "last_check": now,
            "error": None,
        }
    else:
        return {
            "status": "unknown",
            "configured": False,
            "last_check": now,
            "error": f"Unknown integration: {integration}",
        }
    
    return {
        "status": status,
        "configured": configured,
        "last_check": now,
        "error": error,
    }
