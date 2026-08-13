"""Shopify OAuth request / response DTOs (RULE API-004)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# A Shopify shop domain is always <name>.myshopify.com (SEC-031 allowlist).
SHOP_DOMAIN_PATTERN = r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$"


class InstallRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    shop_domain: str = Field(pattern=SHOP_DOMAIN_PATTERN, max_length=255)


class InstallResponse(BaseModel):
    install_url: str


class CallbackQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=512)
    state: str = Field(min_length=10, max_length=512)
    shop: str = Field(pattern=SHOP_DOMAIN_PATTERN, max_length=255)
    hmac: str = Field(min_length=1, max_length=512)
    timestamp: str = Field(min_length=1, max_length=32)


class ConnectionResponse(BaseModel):
    id: str
    workspace_id: str
    shop_domain: str
    shop_name: str
    scopes: str
    status: str
    installed_at: datetime
    disconnected_at: datetime | None = None
    last_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StatusResponse(BaseModel):
    connected: bool
    connection: ConnectionResponse | None = None


class MessageResponse(BaseModel):
    message: str


class SyncRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resources: list[str] = Field(default_factory=lambda: ["orders", "products", "customers"])


class SyncResponse(BaseModel):
    job_id: str
    status: str
    counts: dict = Field(default_factory=dict)


class SyncStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    counts: dict = Field(default_factory=dict)


class OrderResponse(BaseModel):
    id: str
    shopify_id: int
    order_number: int | None = None
    customer_id: int | None = None
    currency: str | None = None
    subtotal: float
    tax: float
    shipping: float
    discount: float
    total: float
    status: str | None = None
    financial_status: str | None = None
    fulfillment_status: str | None = None
    payment_gateway_names: list[str] = Field(default_factory=list)
    presentment_currency: str | None = None
    gift_card_amount_used: float
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProductResponse(BaseModel):
    id: str
    shopify_id: int
    title: str
    handle: str | None = None
    product_type: str | None = None
    vendor: str | None = None
    status: str | None = None
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CustomerResponse(BaseModel):
    id: str
    shopify_id: int
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    tags: list[str] = Field(default_factory=list)
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OrderPage(BaseModel):
    items: list[OrderResponse]
    page: int
    size: int
    total: int
    total_pages: int


class ProductPage(BaseModel):
    items: list[ProductResponse]
    page: int
    size: int
    total: int
    total_pages: int


class CustomerPage(BaseModel):
    items: list[CustomerResponse]
    page: int
    size: int
    total: int
    total_pages: int


class WebhookEventResponse(BaseModel):
    event_id: str
    topic: str
    shop_domain: str
    processed: bool
    received_at: datetime
    error: str | None = None


class WebhookStatusResponse(BaseModel):
    total: int
    processed: int
    unprocessed: int
    recent: list[WebhookEventResponse]


# --- Milestone 3: Razorpay Integration ---


class RazorpayConnectRequest(BaseModel):
    """ARCH-AUDIT-001 fix: each workspace connects its own Razorpay account.
    key_secret and webhook_secret are encrypted at rest and never returned."""

    model_config = ConfigDict(str_strip_whitespace=True)

    key_id: str = Field(min_length=8, max_length=128)
    key_secret: str = Field(min_length=8, max_length=256)
    webhook_secret: str | None = Field(default=None, min_length=8, max_length=256)


class RazorpayConnectionResponse(BaseModel):
    id: str
    workspace_id: str
    key_id: str
    account_name: str | None = None
    account_email: str | None = None
    status: str
    installed_at: datetime
    disconnected_at: datetime | None = None
    last_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RazorpayStatusResponse(BaseModel):
    connected: bool
    connection: RazorpayConnectionResponse | None = None


class RazorpayPaymentResponse(BaseModel):
    id: str
    razorpay_id: str
    order_id: str | None = None
    amount: float
    currency: str | None = None
    status: str | None = None
    method: str | None = None
    fee: float
    tax: float
    captured: bool
    refunded: bool
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RazorpayRefundResponse(BaseModel):
    id: str
    razorpay_id: str
    payment_id: str | None = None
    amount: float
    currency: str | None = None
    status: str | None = None
    reason: str | None = None
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RazorpaySettlementResponse(BaseModel):
    id: str
    razorpay_id: str
    amount: float
    currency: str | None = None
    status: str | None = None
    fee: float
    tax: float
    settled_at: datetime | None = None
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RazorpayPaymentPage(BaseModel):
    items: list[RazorpayPaymentResponse]
    page: int
    size: int
    total: int
    total_pages: int


class RazorpayRefundPage(BaseModel):
    items: list[RazorpayRefundResponse]
    page: int
    size: int
    total: int
    total_pages: int


class RazorpaySettlementPage(BaseModel):
    items: list[RazorpaySettlementResponse]
    page: int
    size: int
    total: int
    total_pages: int


# --- Milestone 4: Financial Reconciliation Engine ---


class ReconciliationJobResponse(BaseModel):
    id: str
    workspace_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    counts: dict = Field(default_factory=dict)
    date_from: datetime | None = None
    date_to: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReconciliationResultResponse(BaseModel):
    id: str
    workspace_id: str
    job_id: str
    match_status: str
    shopify_order_id: int | None = None
    razorpay_order_id: str | None = None
    shopify_payment_ids: list[str] = Field(default_factory=list)
    razorpay_payment_ids: list[str] = Field(default_factory=list)
    shopify_refund_ids: list[str] = Field(default_factory=list)
    razorpay_refund_ids: list[str] = Field(default_factory=list)
    shopify_settlement_ids: list[str] = Field(default_factory=list)
    razorpay_settlement_ids: list[str] = Field(default_factory=list)
    amount_shopify: float
    amount_razorpay: float
    amount_difference: float
    currency: str | None = None
    confidence: float
    reason: str | None = None
    # ARCH-AUDIT-009 fix: additive fields so every result carries the
    # Evidence / Business Rule / Calculation / Explanation / Recommendation
    # the product spec requires. Optional so existing clients parsing this
    # response are unaffected.
    evidence: dict | None = None
    business_rule: str | None = None
    calculation: str | None = None
    explanation: str | None = None
    recommendation: str | None = None
    created_at: datetime
    updated_at: datetime
    id: str
    workspace_id: str
    job_id: str
    result_id: str | None = None
    exception_type: str
    severity: str
    status: str
    shopify_order_id: int | None = None
    razorpay_order_id: str | None = None
    payment_id: str | None = None
    settlement_id: str | None = None
    amount: float
    currency: str | None = None
    root_cause: str | None = None
    suggested_action: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None
    created_at: datetime
    updated_at: datetime


class ReconciliationResultPage(BaseModel):
    items: list[ReconciliationResultResponse]
    page: int
    size: int
    total: int
    total_pages: int


class ReconciliationExceptionPage(BaseModel):
    items: list[ReconciliationExceptionResponse]
    page: int
    size: int
    total: int
    total_pages: int


class ReconciliationSummaryResponse(BaseModel):
    total_orders: int
    matched: int
    partial_match: int
    unmatched: int
    missing_payment: int
    ghost_order: int
    duplicate_payment: int
    refund_mismatch: int
    settlement_mismatch: int
    manual_review: int
    match_rate: float
    confidence_score: float


# --- Milestone 5: Dashboard & Analytics ---


class DashboardOverviewResponse(BaseModel):
    revenue: float
    total_orders: int
    total_payments: float
    total_refunds: float
    total_settlements: float
    reconciliation_match_rate: float
    total_exceptions: int
    critical_exceptions: int
    pending_exceptions: int
    connected_integrations: int
    # ARCH-AUDIT-007 fix: additive field, Money At Risk total.
    money_at_risk: float = 0.0


class MoneyAtRiskBreakdown(BaseModel):
    amount: float
    count: int


class MoneyAtRiskResponse(BaseModel):
    total_amount: float
    currency: str | None = None
    open_exception_count: int
    by_exception_type: dict[str, MoneyAtRiskBreakdown] = Field(default_factory=dict)


class RevenueResponse(BaseModel):
    total: float
    currency: str | None = None
    daily: list[dict] = Field(default_factory=list)
    weekly: list[dict] = Field(default_factory=list)
    monthly: list[dict] = Field(default_factory=list)


class OrdersResponse(BaseModel):
    total: int
    trend: list[dict] = Field(default_factory=list)


class PaymentsResponse(BaseModel):
    total: float
    trend: list[dict] = Field(default_factory=list)


class RefundsResponse(BaseModel):
    total: float
    trend: list[dict] = Field(default_factory=list)


class SettlementsResponse(BaseModel):
    total: float
    trend: list[dict] = Field(default_factory=list)


class ExceptionsResponse(BaseModel):
    total: int
    critical: int
    pending: int
    trend: list[dict] = Field(default_factory=list)


class MatchRateResponse(BaseModel):
    rate: float
    trend: list[dict] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    revenue: RevenueResponse
    orders: OrdersResponse
    payments: PaymentsResponse
    refunds: RefundsResponse
    settlements: SettlementsResponse
    exceptions: ExceptionsResponse
    match_rate: MatchRateResponse


# --- Milestone 6: Production Readiness ---


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(csv|excel|pdf)$", description="Export format: csv, excel, or pdf")
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: str | None = None
    match_status: str | None = None
    exception_type: str | None = None
    severity: str | None = None
    payment_id: str | None = None
    order_id: str | None = None
    shop_domain: str | None = None


class ExportResponse(BaseModel):
    download_url: str
    filename: str
    format: str
    record_count: int


class NotificationPreferenceResponse(BaseModel):
    id: str
    workspace_id: str
    critical_reconciliation_failures: bool = True
    failed_shopify_sync: bool = True
    failed_razorpay_sync: bool = True
    oauth_expiration: bool = True
    webhook_failures: bool = True
    email_enabled: bool = False
    webhook_url: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    critical_reconciliation_failures: bool | None = None
    failed_shopify_sync: bool | None = None
    failed_razorpay_sync: bool | None = None
    oauth_expiration: bool | None = None
    webhook_failures: bool | None = None
    email_enabled: bool | None = None
    webhook_url: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    database: dict
    integrations: dict
    performance: dict | None = None


class DatabaseHealthResponse(BaseModel):
    status: str
    latency_ms: float
    collections: int
    connections: int | None = None


class IntegrationHealthResponse(BaseModel):
    status: str
    configured: bool
    last_check: datetime | None = None
    error: str | None = None
