"""Mongo connection plus the idempotent schema bootstrap (index + seed).

MongoDB has no DDL, so the "migration" step required by the Definition of Done
is implemented here: `bootstrap()` creates every index and seeds the global
permission catalog. It is additive and idempotent, so it is safe to re-run on
every process start.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings

logger = logging.getLogger("ganaka.db")

client = AsyncIOMotorClient(settings.MONGO_URL)
db: AsyncIOMotorDatabase = client[settings.DB_NAME]

# Collections are snake_case and singular per docs/04 RULE DB-005 / DB-006.
USER = "user"
SESSION = "session"
OAUTH_ACCOUNT = "oauth_account"
EMAIL_VERIFICATION_TOKEN = "email_verification_token"
PASSWORD_RESET_TOKEN = "password_reset_token"
WORKSPACE = "workspace"
WORKSPACE_MEMBER = "workspace_member"
WORKSPACE_SETTINGS = "workspace_settings"
WORKSPACE_INVITATION = "workspace_invitation"
ROLE = "role"
PERMISSION = "permission"
AUDIT_LOG = "audit_log"
RATE_LIMIT = "rate_limit"
OUTBOUND_EMAIL = "outbound_email"
SHOPIFY_CONNECTION = "shopify_connection"
SHOPIFY_OAUTH_STATE = "shopify_oauth_state"
SHOPIFY_ORDER = "shopify_order"
SHOPIFY_PRODUCT = "shopify_product"
SHOPIFY_CUSTOMER = "shopify_customer"
SHOPIFY_SYNC_JOB = "shopify_sync_job"
SHOPIFY_WEBHOOK_EVENT = "shopify_webhook_event"
RAZORPAY_CONNECTION = "razorpay_connection"
RAZORPAY_PAYMENT = "razorpay_payment"
RAZORPAY_REFUND = "razorpay_refund"
RAZORPAY_SETTLEMENT = "razorpay_settlement"
RAZORPAY_WEBHOOK_EVENT = "razorpay_webhook_event"
RECONCILIATION_JOB = "reconciliation_job"
RECONCILIATION_RESULT = "reconciliation_result"
RECONCILIATION_EXCEPTION = "reconciliation_exception"
# ARCH-AUDIT-002 fix: generated export files are stored here (short-lived,
# TTL-expired) so the download_url returned by the export endpoints points at
# a real, workspace-scoped file instead of a fabricated URL.
EXPORT_FILE = "export_file"
# ARCH-AUDIT-003 fix: delivery attempts for notifications (email/webhook) are
# logged here so failures are visible and auditable rather than silently
# swallowed.
NOTIFICATION_DELIVERY_LOG = "notification_delivery_log"

PERMISSION_CATALOG = [
    ("workspace.read", "WORKSPACE", "View workspace details"),
    ("workspace.update", "WORKSPACE", "Update workspace details"),
    ("workspace.delete", "WORKSPACE", "Delete a workspace"),
    ("workspace.settings", "WORKSPACE", "Manage workspace settings"),
    ("workspace.members", "WORKSPACE", "Manage workspace members"),
    ("workspace.billing", "WORKSPACE", "Manage workspace billing"),
    ("dashboard.read", "DASHBOARD", "View the dashboard"),
    ("report.read", "REPORT", "View reports"),
    ("report.export", "REPORT", "Export reports"),
    ("shopify.connect", "SHOPIFY", "Connect a Shopify store"),
    ("razorpay.connect", "RAZORPAY", "Connect a Razorpay account"),
    ("finance.read", "FINANCE", "View financial records"),
    ("finance.write", "FINANCE", "Create financial records"),
    ("reconciliation.run", "RECONCILIATION", "Run reconciliation"),
    ("notification.manage", "NOTIFICATION", "Manage notifications"),
    ("admin.access", "ADMIN", "Access administrative functions"),
]

ALL_PERMISSIONS = [code for code, _, _ in PERMISSION_CATALOG]

# implementation/02_WORKSPACE_AND_RBAC.md role definitions.
SYSTEM_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "OWNER": list(ALL_PERMISSIONS),
    "ADMIN": [p for p in ALL_PERMISSIONS if p not in {"workspace.delete", "workspace.billing"}],
    "FINANCE": [
        "workspace.read", "workspace.billing", "dashboard.read", "report.read",
        "report.export", "finance.read", "finance.write", "reconciliation.run",
    ],
    "ACCOUNTANT": [
        "workspace.read", "dashboard.read", "report.read", "report.export", "finance.read",
    ],
    "VIEWER": ["workspace.read", "dashboard.read", "report.read"],
}

ROLE_RANK = {"OWNER": 0, "ADMIN": 1, "FINANCE": 2, "ACCOUNTANT": 3, "VIEWER": 4}


async def bootstrap() -> None:
    await db[USER].create_index([("email", ASCENDING)], unique=True, name="ux_user_email")
    await db[USER].create_index([("status", ASCENDING)], name="ix_user_status")

    await db[SESSION].create_index([("user_id", ASCENDING), ("revoked", ASCENDING)], name="ix_session_user")
    await db[SESSION].create_index([("refresh_token_hash", ASCENDING)], name="ix_session_refresh")
    await db[SESSION].create_index([("expires_at", ASCENDING)], name="ix_session_expiry")

    await db[OAUTH_ACCOUNT].create_index(
        [("provider", ASCENDING), ("provider_user_id", ASCENDING)], unique=True, name="ux_oauth_provider_user"
    )
    await db[OAUTH_ACCOUNT].create_index([("user_id", ASCENDING)], name="ix_oauth_user")

    for coll in (EMAIL_VERIFICATION_TOKEN, PASSWORD_RESET_TOKEN):
        await db[coll].create_index([("token_hash", ASCENDING)], unique=True, name="ux_token_hash")
        await db[coll].create_index([("user_id", ASCENDING)], name="ix_token_user")

    await db[WORKSPACE].create_index([("slug", ASCENDING)], unique=True, name="ux_workspace_slug")
    await db[WORKSPACE].create_index([("owner_id", ASCENDING)], name="ix_workspace_owner")

    await db[WORKSPACE_MEMBER].create_index(
        [("workspace_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="ux_member_workspace_user"
    )
    await db[WORKSPACE_MEMBER].create_index([("user_id", ASCENDING), ("status", ASCENDING)], name="ix_member_user")

    await db[WORKSPACE_SETTINGS].create_index([("workspace_id", ASCENDING)], unique=True, name="ux_settings_workspace")

    await db[WORKSPACE_INVITATION].create_index([("token_hash", ASCENDING)], unique=True, name="ux_invitation_token")
    await db[WORKSPACE_INVITATION].create_index(
        [("workspace_id", ASCENDING), ("email", ASCENDING), ("status", ASCENDING)], name="ix_invitation_lookup"
    )

    await db[ROLE].create_index(
        [("workspace_id", ASCENDING), ("name", ASCENDING)], unique=True, name="ux_role_workspace_name"
    )
    await db[PERMISSION].create_index([("code", ASCENDING)], unique=True, name="ux_permission_code")

    await db[AUDIT_LOG].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_audit_workspace_created"
    )
    await db[AUDIT_LOG].create_index([("actor_user_id", ASCENDING)], name="ix_audit_actor")

    await db[RATE_LIMIT].create_index([("key", ASCENDING)], unique=True, name="ux_rate_limit_key")
    await db[RATE_LIMIT].create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_rate_limit")

    await db[OUTBOUND_EMAIL].create_index([("created_at", DESCENDING)], name="ix_outbound_created")
    await db[OUTBOUND_EMAIL].create_index([("to_email", ASCENDING)], name="ix_outbound_to")

    # Shopify (Feature 2.1). One active connection per workspace and per shop
    # (duplicate prevention); OAuth state nonces are single-use with a TTL.
    await db[SHOPIFY_CONNECTION].create_index(
        [("workspace_id", ASCENDING)], unique=True, name="ux_shopify_connection_workspace"
    )
    await db[SHOPIFY_CONNECTION].create_index(
        [("shop_domain", ASCENDING)], unique=True, name="ux_shopify_connection_shop"
    )
    await db[SHOPIFY_CONNECTION].create_index(
        [("workspace_id", ASCENDING), ("status", ASCENDING)], name="ix_shopify_connection_workspace_status"
    )
    await db[SHOPIFY_OAUTH_STATE].create_index(
        [("state_hash", ASCENDING)], unique=True, name="ux_shopify_oauth_state_hash"
    )
    await db[SHOPIFY_OAUTH_STATE].create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_shopify_oauth_state"
    )

    # Shopify sync (Feature 2.2). Unique (workspace_id, shopify_id) prevents
    # duplicate imports; workspace + timestamp indexes support tenant isolation
    # and the list/filter endpoints.
    for coll in (SHOPIFY_ORDER, SHOPIFY_PRODUCT, SHOPIFY_CUSTOMER):
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("shopify_id", ASCENDING)],
            unique=True,
            name=f"ux_{coll}_workspace_shopify",
        )
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name=f"ix_{coll}_workspace_created"
        )
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("updated_at", DESCENDING)], name=f"ix_{coll}_workspace_updated"
        )
    await db[SHOPIFY_SYNC_JOB].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_shopify_sync_job_workspace_created"
    )

    # Shopify webhooks (Feature 2.3). ARCH-AUDIT-006 fix: dedup is scoped by
    # (shop_domain, payload_hash) rather than a global payload_hash -- a global
    # unique hash meant an identical payload from a SECOND shop would be
    # silently treated as a "duplicate" of the first shop's event and dropped,
    # which is a cross-tenant correctness bug, not just a security nicety.
    try:
        await db[SHOPIFY_WEBHOOK_EVENT].drop_index("ux_shopify_webhook_payload_hash")
    except Exception:  # noqa: BLE001 - fine if the old index never existed
        pass
    await db[SHOPIFY_WEBHOOK_EVENT].create_index(
        [("shop_domain", ASCENDING), ("payload_hash", ASCENDING)],
        unique=True,
        name="ux_shopify_webhook_shop_payload_hash",
    )
    await db[SHOPIFY_WEBHOOK_EVENT].create_index(
        [("shop_domain", ASCENDING), ("processed", ASCENDING)], name="ix_shopify_webhook_shop_processed"
    )
    await db[SHOPIFY_WEBHOOK_EVENT].create_index(
        [("received_at", DESCENDING)], name="ix_shopify_webhook_received"
    )

    # Razorpay (Milestone 3). Unique (workspace_id, razorpay_id) prevents duplicate
    # imports; workspace + timestamp indexes support tenant isolation and list/filter.
    for coll in (RAZORPAY_PAYMENT, RAZORPAY_REFUND, RAZORPAY_SETTLEMENT):
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("razorpay_id", ASCENDING)],
            unique=True,
            name=f"ux_{coll}_workspace_razorpay",
        )
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name=f"ix_{coll}_workspace_created"
        )
        await db[coll].create_index(
            [("workspace_id", ASCENDING), ("updated_at", DESCENDING)], name=f"ix_{coll}_workspace_updated"
        )
    # ARCH-AUDIT-001/008 fix: the old index made workspace_id unique across
    # ALL statuses, which meant a workspace could never reconnect Razorpay
    # after disconnecting (the DISCONNECTED doc would permanently block a new
    # insert) even though disconnect_razorpay()'s own docstring promises
    # "allows reconnect." Scope the uniqueness to ACTIVE connections only
    # (standard partial-unique-index pattern) and drop the old, stricter
    # index if a prior deployment already created it.
    try:
        await db[RAZORPAY_CONNECTION].drop_index("ux_razorpay_connection_workspace")
    except Exception:  # noqa: BLE001 - fine if the old index never existed
        pass
    await db[RAZORPAY_CONNECTION].create_index(
        [("workspace_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": "ACTIVE"},
        name="ux_razorpay_connection_workspace_active",
    )
    # Webhook dedup is scoped per-workspace (ARCH-AUDIT-006 fix, same class of
    # issue for Razorpay as Shopify): a payload hash colliding across two
    # different tenants' accounts must not silently drop the second tenant's
    # event as a "duplicate".
    try:
        await db[RAZORPAY_WEBHOOK_EVENT].drop_index("ux_razorpay_webhook_payload_hash")
    except Exception:  # noqa: BLE001 - fine if the old index never existed
        pass
    await db[RAZORPAY_WEBHOOK_EVENT].create_index(
        [("workspace_id", ASCENDING), ("payload_hash", ASCENDING)],
        unique=True,
        name="ux_razorpay_webhook_workspace_payload_hash",
    )
    await db[RAZORPAY_WEBHOOK_EVENT].create_index(
        [("received_at", DESCENDING)], name="ix_razorpay_webhook_received"
    )

    # Reconciliation (Milestone 4). Unique job idempotency key prevents duplicate
    # runs; workspace + timestamp indexes support the list endpoints.
    await db[RECONCILIATION_JOB].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_recon_job_workspace_created"
    )
    await db[RECONCILIATION_JOB].create_index(
        [("idempotency_key", ASCENDING)], unique=True, name="ux_recon_job_idempotency"
    )
    await db[RECONCILIATION_RESULT].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_recon_result_workspace_created"
    )
    await db[RECONCILIATION_RESULT].create_index(
        [("workspace_id", ASCENDING), ("match_status", ASCENDING)], name="ix_recon_result_status"
    )
    await db[RECONCILIATION_EXCEPTION].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_recon_exception_workspace_created"
    )
    await db[RECONCILIATION_EXCEPTION].create_index(
        [("workspace_id", ASCENDING), ("status", ASCENDING)], name="ix_recon_exception_status"
    )

    # Exports (ARCH-AUDIT-002 fix). TTL-expired: generated files are
    # short-lived, downloadable exactly once the export call returns, and
    # workspace-scoped so download requires matching workspace_id.
    await db[EXPORT_FILE].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_export_file_workspace_created"
    )
    await db[EXPORT_FILE].create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_export_file_expires"
    )

    # Notification delivery log (ARCH-AUDIT-003 fix).
    await db[NOTIFICATION_DELIVERY_LOG].create_index(
        [("workspace_id", ASCENDING), ("created_at", DESCENDING)], name="ix_notification_log_workspace_created"
    )

    for code, category, description in PERMISSION_CATALOG:
        await db[PERMISSION].update_one(
            {"code": code},
            {"$set": {"code": code, "category": category, "description": description}, "$setOnInsert": {"_id": code}},
            upsert=True,
        )

    logger.info("schema_bootstrap_complete collections=%s", len(await db.list_collection_names()))
