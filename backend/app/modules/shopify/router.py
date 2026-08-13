"""Shopify OAuth + sync controllers (Features 2.1/2.2), plus Razorpay (M3),
Reconciliation (M4), Dashboard (M5), Exports / Notifications / Health (M6).

Each concern is mounted on its own documented path prefix. No business logic
lives in controllers (RULE API-005).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo import DESCENDING

from app.core import audit
from app.core import db as database
from app.core.config import settings
from app.core.deps import AuthContext, require_permission
from app.core.models import new_id, utc_now
from app.core.pagination import PageRequest
from app.core.rate_limit import enforce
from app.modules.shopify import service
from app.modules.shopify.schemas import (
    AnalyticsResponse,
    CallbackQuery,
    ConnectionResponse,
    CustomerPage,
    DashboardOverviewResponse,
    MoneyAtRiskResponse,
    ExceptionsResponse,
    InstallRequest,
    InstallResponse,
    MatchRateResponse,
    MessageResponse,
    OrderPage,
    OrdersResponse,
    PaymentsResponse,
    ProductPage,
    RefundsResponse,
    RevenueResponse,
    SettlementsResponse,
    StatusResponse,
    SyncRequest,
    SyncResponse,
    SyncStatusResponse,
    RazorpayConnectionResponse,
    RazorpayConnectRequest,
    RazorpayPaymentPage,
    RazorpayRefundPage,
    RazorpaySettlementPage,
    RazorpayStatusResponse,
    ReconciliationExceptionPage,
    ReconciliationJobResponse,
    ReconciliationResultPage,
    ReconciliationSummaryResponse,
    WebhookStatusResponse,
    ExportRequest,
    ExportResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    HealthResponse,
    DatabaseHealthResponse,
    IntegrationHealthResponse,
)

# ---------------------------------------------------------------------------
# Shopify (Feature 2.1 / 2.2 / 2.3)
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/shopify", tags=["Shopify"])


@router.post(
    "/install",
    response_model=InstallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Shopify OAuth install URL",
    description="Requires shopify.connect. Returns the Shopify authorization URL for the "
    "workspace's store. Rejects if the workspace already has an active connection.",
)
async def install(
    payload: InstallRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("shopify.connect")),
):
    await enforce("shopify.install", request)
    return await service.generate_install_url(context, payload.shop_domain)


@router.get(
    "/callback",
    response_model=ConnectionResponse,
    summary="Complete the Shopify OAuth flow",
    description="Requires shopify.connect. Verifies the callback HMAC, consumes the single-use "
    "state nonce, exchanges the code for an access token, validates the store, encrypts the "
    "token and persists the connection.",
)
async def callback(
    query: CallbackQuery = Depends(),
    request: Request = None,
    context: AuthContext = Depends(require_permission("shopify.connect")),
):
    await enforce("shopify.callback", request)
    return await service.handle_callback(context, query.model_dump(), request)


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Get the workspace's Shopify connection status",
    description="Requires shopify.connect. Returns whether the workspace has an active "
    "Shopify connection and its details (never the access token).",
)
async def status(context: AuthContext = Depends(require_permission("shopify.connect"))):
    return await service.get_status(context)


@router.delete(
    "/disconnect",
    response_model=MessageResponse,
    summary="Disconnect the workspace's Shopify store",
    description="Requires shopify.connect. Marks the connection DISCONNECTED so the store can "
    "be reconnected later. The encrypted token is retained for audit but never returned.",
)
async def disconnect(
    request: Request, context: AuthContext = Depends(require_permission("shopify.connect"))
):
    await enforce("shopify.disconnect", request)
    return await service.disconnect(context, request)


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Run an initial full sync of Shopify data",
    description="Requires shopify.connect. Imports orders, products and customers (initial "
    "full sync, idempotent by shopify_id). Returns the sync job id.",
)
async def sync(
    payload: SyncRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("shopify.connect")),
):
    await enforce("shopify.sync", request)
    return await service.run_sync(context, payload.resources, request)


@router.get(
    "/sync/status/{job_id}",
    response_model=SyncStatusResponse,
    summary="Get a Shopify sync job's status",
    description="Requires shopify.connect. Returns COMPLETED/FAILED/RUNNING with the counts "
    "per resource. The job must belong to the authenticated workspace.",
)
async def sync_status(
    job_id: str, context: AuthContext = Depends(require_permission("shopify.connect"))
):
    return await service.get_sync_status(context, job_id)


@router.get(
    "/orders",
    response_model=OrderPage,
    summary="List the workspace's Shopify orders",
    description="Requires finance.read. Paginated (page/page_size/sort). Filters: "
    "financial_status, created_from, created_to. The workspace is derived from the "
    "token, never the client.",
)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    financial_status: str | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("finance.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_orders(context, page_request, financial_status, created_from, created_to)


@router.get(
    "/products",
    response_model=ProductPage,
    summary="List the workspace's Shopify products",
    description="Requires workspace.read. Paginated (page/page_size/sort).",
)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_products(context, page_request)


@router.get(
    "/customers",
    response_model=CustomerPage,
    summary="List the workspace's Shopify customers",
    description="Requires workspace.read. Paginated (page/page_size/sort).",
)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_customers(context, page_request)


@router.post(
    "/webhooks",
    summary="Receive a Shopify webhook (public, HMAC-verified)",
    description="Public endpoint authenticated via Shopify HMAC signature. Verifies the "
    "webhook, deduplicates by payload hash, stores the event, and applies incremental "
    "sync. Never processes an invalid webhook.",
)
async def receive_webhook(request: Request):
    payload = await request.body()
    topic = request.headers.get("X-Shopify-Topic", "")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")
    event_id = request.headers.get("X-Shopify-Webhook-Id", "")
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")
    result = await service.process_webhook_event(payload, topic, shop_domain, event_id, hmac_header, request)
    return result


@router.post(
    "/webhooks/test",
    response_model=MessageResponse,
    summary="Test webhook processing (authenticated)",
    description="Requires shopify.connect. Accepts a test payload and processes it through "
    "the webhook pipeline without actually receiving an HTTP webhook from Shopify.",
)
async def test_webhook(
    request: Request,
    context: AuthContext = Depends(require_permission("shopify.connect")),
):
    # ARCH-AUDIT-012 fix: this endpoint replays arbitrary payloads through the
    # real webhook pipeline and has no business being reachable in production.
    if not settings.ENABLE_TEST_ENDPOINTS or settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not Found")
    payload = await request.body()
    topic = request.headers.get("X-Shopify-Topic", "orders/create")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")
    event_id = request.headers.get("X-Shopify-Webhook-Id", str(new_id()))
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")
    if not hmac_header:
        # For test endpoint, use a dummy HMAC if not provided.
        hmac_header = "test"
    result = await service.process_webhook_event(payload, topic, shop_domain, event_id, hmac_header, request)
    return {"message": f"Webhook test processed: {result.get('status')}"}


@router.post(
    "/sync/incremental",
    response_model=SyncResponse,
    summary="Run an incremental sync (manual trigger)",
    description="Requires shopify.connect. Triggers an incremental sync job for the "
    "workspace's active connection. Returns the job id, and the returned status always "
    "matches what was persisted for the job.",
)
async def incremental_sync(
    request: Request,
    context: AuthContext = Depends(require_permission("shopify.connect")),
):
    await enforce("shopify.sync.incremental", request)
    return await service.run_incremental_sync(context, request)


@router.get(
    "/webhooks/status",
    response_model=WebhookStatusResponse,
    summary="Get webhook event status for the workspace",
    description="Requires shopify.connect. Returns total/processed/unprocessed counts and "
    "the 10 most recent webhook events for the workspace's shop.",
)
async def webhook_status(
    context: AuthContext = Depends(require_permission("shopify.connect"))
):
    return await service.get_webhook_status(context)


# ---------------------------------------------------------------------------
# Razorpay (Milestone 3)
# ---------------------------------------------------------------------------

razorpay_router = APIRouter(prefix="/razorpay", tags=["Razorpay"])


@razorpay_router.post(
    "/connect",
    response_model=RazorpayConnectionResponse,
    summary="Connect a Razorpay account",
    description="Requires razorpay.connect. Accepts this workspace's own Razorpay key_id, "
    "key_secret and (optional) webhook_secret, verifies them against the live Razorpay API, "
    "and stores the secrets encrypted (AES-256-GCM). The secrets are never returned to the "
    "client. Each workspace connects its own account -- no platform-wide credential is used.",
)
async def razorpay_connect(
    payload: RazorpayConnectRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("razorpay.connect")),
):
    await enforce("razorpay.connect", request)
    return await service.connect_razorpay(context, payload, request)


@razorpay_router.post(
    "/webhooks",
    response_model=MessageResponse,
    summary="Receive a Razorpay webhook",
    description="Public endpoint (no auth -- Razorpay calls this directly). Verifies "
    "X-Razorpay-Signature against each active workspace's own webhook secret to resolve the "
    "tenant, deduplicates by (workspace_id, payload hash), and upserts the resulting "
    "payment/refund/settlement record.",
)
async def razorpay_webhook(request: Request):
    await enforce("razorpay.webhook", request)
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    result = await service.process_razorpay_webhook_event(payload, signature, request)
    return {"message": f"Razorpay webhook {result.get('status')}"}


@razorpay_router.delete(
    "/disconnect",
    response_model=MessageResponse,
    summary="Disconnect the workspace's Razorpay account",
    description="Requires razorpay.connect. Marks the connection DISCONNECTED so the "
    "account can be reconnected later. The encrypted key secret is retained for audit.",
)
async def razorpay_disconnect(
    request: Request,
    context: AuthContext = Depends(require_permission("razorpay.connect")),
):
    await enforce("razorpay.disconnect", request)
    return await service.disconnect_razorpay(context, request)


@razorpay_router.get(
    "/status",
    response_model=RazorpayStatusResponse,
    summary="Get the workspace's Razorpay connection status",
    description="Requires razorpay.connect. Returns whether the workspace has an active "
    "Razorpay connection and its details (never the key secret).",
)
async def razorpay_status(context: AuthContext = Depends(require_permission("razorpay.connect"))):
    return await service.get_razorpay_status(context)


@razorpay_router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Run a manual sync of Razorpay data",
    description="Requires razorpay.connect. Syncs payments, refunds and settlements from "
    "Razorpay. Returns the sync job id and counts.",
)
async def razorpay_sync(
    request: Request,
    context: AuthContext = Depends(require_permission("razorpay.connect")),
):
    await enforce("razorpay.sync", request)
    return await service.run_razorpay_sync(context, request)


@razorpay_router.get(
    "/payments",
    response_model=RazorpayPaymentPage,
    summary="List the workspace's Razorpay payments",
    description="Requires finance.read. Paginated (page/page_size/sort). Filters: status, "
    "payment_id, order_id, date_from, date_to.",
)
async def list_razorpay_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    status: str | None = Query(None),
    payment_id: str | None = Query(None),
    order_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("finance.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_razorpay_payments(context, page_request, status, payment_id, order_id, date_from, date_to)


@razorpay_router.get(
    "/refunds",
    response_model=RazorpayRefundPage,
    summary="List the workspace's Razorpay refunds",
    description="Requires finance.read. Paginated (page/page_size/sort). Filters: status, "
    "payment_id, date_from, date_to.",
)
async def list_razorpay_refunds(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    status: str | None = Query(None),
    payment_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("finance.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_razorpay_refunds(context, page_request, status, payment_id, date_from, date_to)


@razorpay_router.get(
    "/settlements",
    response_model=RazorpaySettlementPage,
    summary="List the workspace's Razorpay settlements",
    description="Requires finance.read. Paginated (page/page_size/sort). Filters: status, "
    "date_from, date_to.",
)
async def list_razorpay_settlements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("finance.read")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_razorpay_settlements(context, page_request, status, date_from, date_to)


# ---------------------------------------------------------------------------
# Reconciliation (Milestone 4)
# ---------------------------------------------------------------------------

reconciliation_router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@reconciliation_router.post(
    "/run",
    response_model=ReconciliationJobResponse,
    summary="Run reconciliation for the workspace",
    description="Requires reconciliation.run. Runs the reconciliation engine for the "
    "workspace within the optional date range. Returns the job id and status.",
)
async def run_reconciliation(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    request: Request = None,
    context: AuthContext = Depends(require_permission("reconciliation.run")),
):
    await enforce("reconciliation.run", request)
    return await service.run_reconciliation(context, date_from, date_to, request)


@reconciliation_router.get(
    "/results",
    response_model=ReconciliationResultPage,
    summary="List reconciliation results",
    description="Requires reconciliation.run. Paginated (page/page_size/sort). "
    "Filters: match_status, date_from, date_to.",
)
async def list_reconciliation_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    match_status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("reconciliation.run")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_reconciliation_results(context, page_request, match_status, date_from, date_to)


@reconciliation_router.get(
    "/exceptions",
    response_model=ReconciliationExceptionPage,
    summary="List reconciliation exceptions",
    description="Requires reconciliation.run. Paginated (page/page_size/sort). "
    "Filters: status, exception_type.",
)
async def list_reconciliation_exceptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    status: str | None = Query(None),
    exception_type: str | None = Query(None),
    context: AuthContext = Depends(require_permission("reconciliation.run")),
):
    page_request = PageRequest()
    page_request.page = page
    page_request.size = page_size
    page_request.sort_raw = sort
    return await service.list_reconciliation_exceptions(context, page_request, status, exception_type)


@reconciliation_router.get(
    "/summary",
    response_model=ReconciliationSummaryResponse,
    summary="Get reconciliation summary",
    description="Requires reconciliation.run. Returns aggregate counts and match rate "
    "for the workspace within the optional date range.",
)
async def get_reconciliation_summary(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("reconciliation.run")),
):
    return await service.get_reconciliation_summary(context, date_from, date_to)


# ---------------------------------------------------------------------------
# Dashboard (Milestone 5)
# ---------------------------------------------------------------------------

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="Get dashboard overview cards",
    description="Requires dashboard.read. Returns revenue, orders, payments, refunds, "
    "settlements, reconciliation match rate, exceptions, and connected integrations "
    "for the workspace within the optional date range.",
)
async def dashboard_overview(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_overview(context, date_from, date_to)


@dashboard_router.get(
    "/revenue",
    response_model=RevenueResponse,
    summary="Get revenue overview with trends",
    description="Requires dashboard.read. Returns total revenue and daily/weekly/monthly "
    "trends for the workspace within the optional date range.",
)
async def dashboard_revenue(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_revenue(context, date_from, date_to)


@dashboard_router.get(
    "/orders",
    response_model=OrdersResponse,
    summary="Get orders count with trend",
    description="Requires dashboard.read. Returns total orders and daily trend for the "
    "workspace within the optional date range.",
)
async def dashboard_orders(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_orders(context, date_from, date_to)


@dashboard_router.get(
    "/payments",
    response_model=PaymentsResponse,
    summary="Get payments total with trend",
    description="Requires dashboard.read. Returns total payments and daily trend for the "
    "workspace within the optional date range.",
)
async def dashboard_payments(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_payments(context, date_from, date_to)


@dashboard_router.get(
    "/refunds",
    response_model=RefundsResponse,
    summary="Get refunds total with trend",
    description="Requires dashboard.read. Returns total refunds and daily trend for the "
    "workspace within the optional date range.",
)
async def dashboard_refunds(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_refunds(context, date_from, date_to)


@dashboard_router.get(
    "/settlements",
    response_model=SettlementsResponse,
    summary="Get settlements total with trend",
    description="Requires dashboard.read. Returns total settlements and daily trend for the "
    "workspace within the optional date range.",
)
async def dashboard_settlements(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_settlements(context, date_from, date_to)


@dashboard_router.get(
    "/exceptions",
    response_model=ExceptionsResponse,
    summary="Get exception counts with trend",
    description="Requires dashboard.read. Returns total, critical, and pending exception "
    "counts with daily trend for the workspace within the optional date range.",
)
async def dashboard_exceptions(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_exceptions(context, date_from, date_to)


@dashboard_router.get(
    "/match-rate",
    response_model=MatchRateResponse,
    summary="Get reconciliation match rate with trend",
    description="Requires dashboard.read. Returns the overall match rate and daily trend "
    "for the workspace within the optional date range.",
)
async def dashboard_match_rate(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_match_rate(context, date_from, date_to)


@dashboard_router.get(
    "/money-at-risk",
    response_model=MoneyAtRiskResponse,
    summary="Get Money At Risk",
    description="Requires dashboard.read. ARCH-AUDIT-007: total value tied up in OPEN "
    "reconciliation exceptions (ghost orders, missing payments, duplicates, settlement and "
    "refund mismatches), broken down by exception type, for the workspace within the "
    "optional date range.",
)
async def dashboard_money_at_risk(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_money_at_risk(context, date_from, date_to)


@dashboard_router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get full analytics payload",
    description="Requires dashboard.read. Returns revenue, orders, payments, refunds, "
    "settlements, exceptions, and match rate with trends in a single response.",
)
async def dashboard_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    context: AuthContext = Depends(require_permission("dashboard.read")),
):
    return await service.get_dashboard_analytics(context, date_from, date_to)


# ---------------------------------------------------------------------------
# Exports (Milestone 6)
# ---------------------------------------------------------------------------

exports_router = APIRouter(prefix="/exports", tags=["Exports"])


@exports_router.post(
    "/reconciliation-results",
    response_model=ExportResponse,
    summary="Export reconciliation results",
    description="Requires report.export. Exports reconciliation results as CSV, Excel, or PDF "
    "with optional filters. Returns a download URL.",
)
async def export_reconciliation_results(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_reconciliation_results(context, export_request)


@exports_router.post(
    "/exceptions",
    response_model=ExportResponse,
    summary="Export reconciliation exceptions",
    description="Requires report.export. Exports reconciliation exceptions as CSV, Excel, or PDF "
    "with optional filters. Returns a download URL.",
)
async def export_exceptions(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_exceptions(context, export_request)


@exports_router.post(
    "/dashboard-summary",
    response_model=ExportResponse,
    summary="Export dashboard summary",
    description="Requires report.export. Exports dashboard summary as CSV, Excel, or PDF. "
    "Returns a download URL.",
)
async def export_dashboard_summary(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_dashboard_summary(context, export_request)


@exports_router.post(
    "/payments",
    response_model=ExportResponse,
    summary="Export payments",
    description="Requires report.export. Exports payments as CSV, Excel, or PDF with optional "
    "filters. Returns a download URL.",
)
async def export_payments(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_payments(context, export_request)


@exports_router.post(
    "/refunds",
    response_model=ExportResponse,
    summary="Export refunds",
    description="Requires report.export. Exports refunds as CSV, Excel, or PDF with optional "
    "filters. Returns a download URL.",
)
async def export_refunds(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_refunds(context, export_request)


@exports_router.post(
    "/settlements",
    response_model=ExportResponse,
    summary="Export settlements",
    description="Requires report.export. Exports settlements as CSV, Excel, or PDF with optional "
    "filters. Returns a download URL.",
)
async def export_settlements(
    export_request: ExportRequest,
    context: AuthContext = Depends(require_permission("report.export")),
):
    return await service.export_settlements(context, export_request)


@exports_router.get(
    "/download/{filename}",
    summary="Download a previously generated export file",
    description="Requires report.export. ARCH-AUDIT-002 fix: this is now a real endpoint -- "
    "the download_url returned by every /exports/* call resolves here. Files are "
    "workspace-scoped (a request for another workspace's file returns 404) and expire "
    "24 hours after generation.",
)
async def download_export(
    filename: str,
    context: AuthContext = Depends(require_permission("report.export")),
):
    content, content_type, safe_filename = await service.download_export(context, filename)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


# ---------------------------------------------------------------------------
# Notifications (Milestone 6)
# ---------------------------------------------------------------------------

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
    description="Requires workspace.read. Returns the workspace's notification preferences.",
)
async def get_notification_preferences(
    context: AuthContext = Depends(require_permission("workspace.read")),
):
    return await service.get_notification_preferences(context)


@notifications_router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preferences",
    description="Requires workspace.update. Updates the workspace's notification preferences.",
)
async def update_notification_preferences(
    update_data: NotificationPreferenceUpdate,
    context: AuthContext = Depends(require_permission("workspace.update")),
):
    return await service.update_notification_preferences(context, update_data)


# ---------------------------------------------------------------------------
# Health (Milestone 6)
# ---------------------------------------------------------------------------

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get(
    "",
    response_model=HealthResponse,
    summary="Get overall health status",
    description="Public endpoint. Returns the overall health status of the application, "
    "including database and integrations.",
)
async def health():
    return await service.get_health_status()


@health_router.get(
    "/database",
    response_model=DatabaseHealthResponse,
    summary="Get database health",
    description="Public endpoint. Returns detailed database health information.",
)
async def health_database():
    return await service.get_database_health()


@health_router.get(
    "/shopify",
    response_model=IntegrationHealthResponse,
    summary="Get Shopify integration health",
    description="Public endpoint. Returns the health status of the Shopify integration.",
)
async def health_shopify():
    return await service.get_integration_health("shopify")


@health_router.get(
    "/razorpay",
    response_model=IntegrationHealthResponse,
    summary="Get Razorpay integration health",
    description="Public endpoint. Returns the health status of the Razorpay integration.",
)
async def health_razorpay():
    return await service.get_integration_health("razorpay")


@health_router.get(
    "/reconciliation",
    response_model=IntegrationHealthResponse,
    summary="Get reconciliation engine health",
    description="Public endpoint. Returns the health status of the reconciliation engine.",
)
async def health_reconciliation():
    return await service.get_integration_health("reconciliation")