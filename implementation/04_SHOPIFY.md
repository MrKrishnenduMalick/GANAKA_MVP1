# implementation/04_SHOPIFY.md

---
document:
  id: IMP-004
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

SHOPIFY

owner:

PLATFORM

---

goal:

Connect Shopify stores, securely synchronize commerce data,
maintain webhook integrity and provide reliable order ingestion.

---

CORE_ENTITIES

ShopifyConnection

Shop

Order

OrderItem

Customer

Product

Variant

Inventory

Refund

Fulfillment

Webhook

SyncJob

---

CONNECTION_STATUS

DISCONNECTED

↓

CONNECTING

↓

CONNECTED

↓

SYNCING

↓

ACTIVE

↓

FAILED

↓

RECONNECT_REQUIRED

---

OAUTH_FLOW

User Click Connect

↓

Validate shop domain against `*.myshopify.com` allowlist and reject
private/link-local resolved IPs before issuing any outbound request
(docs/06_SECURITY_REQUIREMENTS.md RULE SEC-031 — SSRF protection).

↓

Redirect Shopify OAuth

↓

Authorization Code

↓

Exchange Access Token

↓

Encrypt Token

↓

Store Credentials

↓

Verify Store

↓

Register Webhooks

↓

Initial Sync

↓

Active

---

SUPPORTED_RESOURCES

Orders

Products

Variants

Customers

Inventory

Refunds

Fulfillments

Transactions

Locations

Collections

---

SYNC_TYPES

Initial Sync

Incremental Sync

Webhook Sync

Manual Sync

Recovery Sync

---

INITIAL_SYNC

Products

↓

Customers

↓

Orders

↓

Transactions

↓

Refunds

↓

Inventory

↓

Complete

---

WEBHOOKS

orders/create

orders/updated

orders/edited (line items / totals changed post-creation — must
re-trigger financial normalization for the affected order)

orders/paid

orders/cancelled

orders/fulfilled

refunds/create

products/create

products/update

inventory/update

app/uninstalled

MANDATORY COMPLIANCE WEBHOOKS (required by Shopify app review —
app submission is rejected without all three; not optional)

customers/data_request — merchant's customer requested their data;
must compile and deliver stored personal data for that customer
within 30 days.

customers/redact — must erase or anonymize PII for a specific
customer (name, email, phone) while preserving anonymized
transaction/financial records for audit (see docs/19_COMPLIANCE_AND_PRIVACY.md
retention rules — financial audit trail is exempt from full deletion,
only direct PII is redacted).

shop/redact — fired 48 hours after app uninstall; must erase or
anonymize all shop-identifying PII. Financial/audit records may be
retained anonymized per docs/17_BACKUP_AND_DISASTER_RECOVERY.md
retention policy.

---

WEBHOOK_FLOW

Receive

↓

Verify HMAC

↓

Validate Shop

↓

Persist Event

↓

Queue Processing

↓

Business Processing

↓

Audit

---

TOKEN_SECURITY

AES256 Encryption

Environment Secret

Rotation Supported

Never Logged

Never Returned To Client

---

SYNC_POLICY

Daily Scheduled

Real-Time Webhooks

Manual Retry

Automatic Retry

Dead Letter Queue

---

RETRY_POLICY

Attempts

5

---

Backoff

Exponential

---

Dead Letter

Enabled

---

IMPORT_RULES

Idempotent

Deduplicate Orders

Ignore Deleted Resources

Track Sync Cursor

Preserve Original IDs

---

ORDER_FIELDS

shopify_order_id

workspace_id

order_number

customer_id

currency

subtotal

tax

shipping

discount

total

status

financial_status

fulfillment_status

payment_gateway_names (array, from Shopify Order.payment_gateway_names —
mandatory field, drives reconciliation eligibility; see
implementation/07_RECONCILIATION_ENGINE.md DISCREPANCY DECISION TABLE
Step 0. Never leave null — if Shopify returns an empty array, store
as ["unknown"] and surface in dashboard for manual classification,
never silently treat as Razorpay-eligible.)

presentment_currency (currency actually charged to customer, may
differ from shop currency; store both, never assume equal)

gift_card_amount_used (DECIMAL, default 0.00 — portion of order
total covered by a Shopify gift card, has no corresponding Razorpay
payment; see docs/22_FINANCIAL_EDGE_CASES.md RULE BR-034. Expected
Razorpay payment amount for matching purposes is always
`order.total - gift_card_amount_used`, never `order.total` alone.)

created_at

updated_at

---

SHOPIFY_REFUND_FIELDS

shopify_refund_id

shopify_order_id

workspace_id

amount

reason

refund_method (enum: ORIGINAL_PAYMENT, STORE_CREDIT, MANUAL — from
Shopify's refund transaction kind. Only ORIGINAL_PAYMENT refunds are
routed into Razorpay refund matching per
docs/22_FINANCIAL_EDGE_CASES.md RULE BR-035; STORE_CREDIT and MANUAL
refunds never generate a REFUND_MISMATCH exception since no Razorpay
refund is expected for them.)

created_at

---

SHOP_FIELDS

shop_domain

shop_name

currency

timezone

country

plan

owner_email

---

API

GET

/api/v1/shopify/connect

GET

/api/v1/shopify/callback

POST

/api/v1/shopify/disconnect

POST

/api/v1/shopify/sync

GET

/api/v1/shopify/status

GET

/api/v1/shopify/orders

GET

/api/v1/shopify/products

POST

/api/v1/shopify/webhook

---

DATABASE

shopify_connections

shopify_orders

shopify_order_items

shopify_products

shopify_variants

shopify_customers

shopify_refunds

shopify_inventory

shopify_webhooks

shopify_sync_jobs

audit_logs

---

EVENTS

SHOPIFY_CONNECTED

SHOPIFY_DISCONNECTED

SHOPIFY_SYNC_STARTED

SHOPIFY_SYNC_COMPLETED

SHOPIFY_SYNC_FAILED

SHOPIFY_WEBHOOK_RECEIVED

SHOPIFY_WEBHOOK_PROCESSED

SHOPIFY_TOKEN_ROTATED

SHOPIFY_APP_UNINSTALLED

CUSTOMER_DATA_REQUESTED

CUSTOMER_DATA_REDACTED

SHOP_DATA_REDACTED

ORDER_EDITED

---

ERRORS

SHOP_NOT_FOUND

INVALID_HMAC

INVALID_TOKEN

TOKEN_EXPIRED

SHOP_ALREADY_CONNECTED

SYNC_FAILED

WEBHOOK_VALIDATION_FAILED

API_RATE_LIMIT

---

MONITORING

OAuth Success

OAuth Failure

Webhook Success

Webhook Failure

Sync Duration

Orders Imported

Products Imported

Refunds Imported

Rate Limit Usage

Retry Count

---

SECURITY

Verify Every Webhook

Encrypt Every Token

Workspace Isolation

RBAC Required

Audit Required

HTTPS Only

Input Validation

---

ACCEPTANCE

✓ OAuth Connection

✓ Token Encryption

✓ Store Verification

✓ Webhook Registration

✓ Initial Sync

✓ Incremental Sync

✓ Manual Sync

✓ Retry Logic

✓ Disconnect

✓ Reconnect

✓ Audit Generated

---

CURSOR_RULES

Never store Shopify tokens in plaintext.

Always verify webhook HMAC.

Always process webhooks asynchronously.

Never duplicate imported orders.

Always use idempotent sync.

Always encrypt credentials.

Always audit connection changes.

Always isolate data by workspace_id.

Never trust webhook payloads without verification.

Never expose Shopify secrets to frontend.

Always store payment_gateway_names verbatim; never assume Razorpay.

Always implement customers/data_request, customers/redact, and
shop/redact — app store submission fails without them.

Always re-normalize financial totals on orders/edited.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE