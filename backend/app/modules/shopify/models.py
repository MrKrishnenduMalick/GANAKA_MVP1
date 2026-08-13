"""Shopify OAuth documents (Feature 2.1)."""

from datetime import datetime

from pydantic import Field

from app.core.models import BaseDocument


class ShopifyConnection(BaseDocument):
    """A workspace's Shopify store connection.

    The access token is stored AES-256-GCM encrypted (implementation/04
    TOKEN_SECURITY) and is never returned to the client.
    """

    workspace_id: str
    shop_domain: str
    shop_name: str
    access_token_encrypted: str
    scopes: str
    installed_at: datetime
    status: str = "ACTIVE"  # ACTIVE|DISCONNECTED
    disconnected_at: datetime | None = None
    last_verified_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class ShopifyOrder(BaseDocument):
    """A Shopify order (Feature 2.2). shopify_id is the original Shopify ID."""

    workspace_id: str
    shopify_id: int
    order_number: int | None = None
    customer_id: int | None = None
    currency: str | None = None
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    status: str | None = None
    financial_status: str | None = None
    fulfillment_status: str | None = None
    payment_gateway_names: list[str] = Field(default_factory=list)
    presentment_currency: str | None = None
    gift_card_amount_used: float = 0.0
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class ShopifyProduct(BaseDocument):
    """A Shopify product (Feature 2.2). shopify_id is the original Shopify ID."""

    workspace_id: str
    shopify_id: int
    title: str
    handle: str | None = None
    product_type: str | None = None
    vendor: str | None = None
    status: str | None = None
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class ShopifyCustomer(BaseDocument):
    """A Shopify customer (Feature 2.2). shopify_id is the original Shopify ID."""

    workspace_id: str
    shopify_id: int
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    tags: list[str] = Field(default_factory=list)
    shopify_created_at: datetime | None = None
    shopify_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class ShopifySyncJob(BaseDocument):
    """A record of a manual sync run (Feature 2.2)."""

    workspace_id: str
    status: str = "RUNNING"  # RUNNING|COMPLETED|FAILED
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    counts: dict = Field(default_factory=dict)
    cursor: dict = Field(default_factory=dict)


class ShopifyWebhookEvent(BaseDocument):
    """A received Shopify webhook event (Feature 2.3)."""

    event_id: str
    topic: str
    shop_domain: str
    processed: bool = False
    received_at: datetime
    payload_hash: str
    error: str | None = None


# --- Milestone 3: Razorpay Integration ---


class RazorpayConnection(BaseDocument):
    """A workspace's Razorpay account connection."""

    workspace_id: str
    key_id: str
    key_secret_encrypted: str
    account_name: str | None = None
    account_email: str | None = None
    installed_at: datetime
    status: str = "ACTIVE"  # ACTIVE|DISCONNECTED
    disconnected_at: datetime | None = None
    last_verified_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class RazorpayPayment(BaseDocument):
    """A Razorpay payment (Milestone 3). razorpay_id is the original Razorpay ID."""

    workspace_id: str
    razorpay_id: str
    order_id: str | None = None
    amount: float = 0.0
    currency: str | None = None
    status: str | None = None
    method: str | None = None
    fee: float = 0.0
    tax: float = 0.0
    captured: bool = False
    refunded: bool = False
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class RazorpayRefund(BaseDocument):
    """A Razorpay refund (Milestone 3)."""

    workspace_id: str
    razorpay_id: str
    payment_id: str | None = None
    amount: float = 0.0
    currency: str | None = None
    status: str | None = None
    reason: str | None = None
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class RazorpaySettlement(BaseDocument):
    """A Razorpay settlement (Milestone 3)."""

    workspace_id: str
    razorpay_id: str
    amount: float = 0.0
    currency: str | None = None
    status: str | None = None
    fee: float = 0.0
    tax: float = 0.0
    settled_at: datetime | None = None
    razorpay_created_at: datetime | None = None
    razorpay_updated_at: datetime | None = None
    raw: dict = Field(default_factory=dict)


class RazorpayWebhookEvent(BaseDocument):
    """A received Razorpay webhook event (Milestone 3)."""

    event_id: str
    topic: str
    processed: bool = False
    received_at: datetime
    payload_hash: str
    error: str | None = None


# --- Milestone 4: Financial Reconciliation Engine ---


class ReconciliationJob(BaseDocument):
    """A reconciliation run (Milestone 4)."""

    workspace_id: str
    status: str = "PENDING"  # PENDING|RUNNING|COMPLETED|FAILED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    counts: dict = Field(default_factory=dict)
    idempotency_key: str
    date_from: datetime | None = None
    date_to: datetime | None = None


class ReconciliationResult(BaseDocument):
    """A single order's reconciliation result (Milestone 4)."""

    workspace_id: str
    job_id: str
    match_status: str  # NOT_APPLICABLE|MATCHED|PARTIAL_MATCH|UNMATCHED|MISSING_PAYMENT|MISSING_ORDER|DUPLICATE|REFUND_MISMATCH|SETTLEMENT_MISMATCH|MANUAL_REVIEW
    shopify_order_id: int | None = None
    razorpay_order_id: str | None = None
    shopify_payment_ids: list[str] = Field(default_factory=list)
    razorpay_payment_ids: list[str] = Field(default_factory=list)
    shopify_refund_ids: list[str] = Field(default_factory=list)
    razorpay_refund_ids: list[str] = Field(default_factory=list)
    shopify_settlement_ids: list[str] = Field(default_factory=list)
    razorpay_settlement_ids: list[str] = Field(default_factory=list)
    amount_shopify: float = 0.0
    amount_razorpay: float = 0.0
    amount_difference: float = 0.0
    currency: str | None = None
    confidence: float = 0.0
    reason: str | None = None
    raw: dict = Field(default_factory=dict)


class ReconciliationException(BaseDocument):
    """An exception requiring manual review (Milestone 4)."""

    workspace_id: str
    job_id: str
    result_id: str | None = None
    exception_type: str  # GHOST_ORDER|MISSING_PAYMENT|DUPLICATE_PAYMENT|SETTLEMENT_MISMATCH|REFUND_MISMATCH|CANCELLED_ORDER_NOT_REFUNDED|SETTLEMENT_DIFFERENCE|TAX_DIFFERENCE|GATEWAY_FEE_DIFFERENCE|UNEXPECTED_ADJUSTMENT
    severity: str  # CRITICAL|WARNING|INFO
    status: str = "OPEN"  # OPEN|RESOLVED|IGNORED
    shopify_order_id: int | None = None
    razorpay_order_id: str | None = None
    payment_id: str | None = None
    settlement_id: str | None = None
    amount: float = 0.0
    currency: str | None = None
    root_cause: str | None = None
    suggested_action: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None
