# implementation/05_RAZORPAY.md

---
document:
  id: IMP-005
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

RAZORPAY

owner:

PLATFORM

---

goal:

Securely integrate Razorpay, synchronize payment and settlement data,
maintain financial integrity and provide reliable reconciliation inputs.

---

CORE_ENTITIES

RazorpayConnection

Payment

Order

Settlement

Refund

Payout

Webhook

SyncJob

WebhookEvent

Balance

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

AUTHENTICATION

PRIMARY METHOD (V1 — use this)

API Key + API Secret, entered directly by the merchant from their
Razorpay Dashboard (Settings → API Keys). No Razorpay approval
required. This is the standard integration method used by
reconciliation/accounting tools and is what V1 must implement.

Webhook Secret (separate value, configured by merchant in Razorpay
Dashboard → Webhooks, used only to verify webhook HMAC signatures —
never used for API calls)

FUTURE METHOD (explicitly out of scope for V1 — do not build)

Razorpay OAuth (Partner Program). Requires Ganaka to be approved as
a Razorpay Partner before this flow can be used at all — a business
/ legal onboarding process with Razorpay, independent of engineering
timeline. Do not implement OAuth token exchange, "Access Token" or
"Refresh Token" concepts for Razorpay until that partner approval
is confirmed. If OAuth is later approved, it will be added as an
alternative connection method alongside API Key entry, not a
replacement.

Validation

Reject any implementation that builds a Razorpay OAuth redirect flow
for V1. Only API Key + Secret + Webhook Secret entry is in scope.

---

CONNECT_FLOW (API Key Method — V1)

User Enters Key ID + Key Secret + Webhook Secret

↓

Validate Format (key_id starts with rzp_, secret non-empty)

↓

Test Call (fetch account balance or similar low-risk read endpoint)

↓

Encrypt Key Secret + Webhook Secret (AES256)

↓

Store Credentials

↓

Register Webhook Endpoint URL In Razorpay Dashboard Instructions
(merchant must paste webhook URL manually — Razorpay API Key auth
does not support programmatic webhook registration the way OAuth
partner apps can; surface this as a clear onboarding step, not a
silent gap)

↓

Initial Sync

↓

ACTIVE

---

SUPPORTED_RESOURCES

Payments

Orders

Settlements

Refunds

Transfers

Payouts

Balance

Disputes

Invoices

---

SYNC_TYPES

Initial Sync

Scheduled Sync

Webhook Sync

Manual Sync

Recovery Sync

---

INITIAL_SYNC

Payments

↓

Orders

↓

Settlements

↓

Refunds

↓

Payouts

↓

Complete

---

WEBHOOKS

payment.authorized

payment.captured

payment.failed

refund.created

refund.processed

settlement.processed

order.paid

invoice.paid

subscription.activated

subscription.cancelled

---

WEBHOOK_PIPELINE

Receive

↓

Verify Signature

↓

Validate Account

↓

Persist Event

↓

Queue

↓

Business Processing

↓

Audit

---

TOKEN_SECURITY

AES256 Encryption

Rotation Supported

Never Logged

Never Returned

Environment Managed

---

IMPORT_RULES

Idempotent

Duplicate Detection

Cursor Tracking

Timezone Normalization

Currency Validation

Immutable Raw Payload

---

PAYMENT_FIELDS

payment_id

workspace_id

order_id

amount

currency

status

method

fee

tax

captured_at

created_at

updated_at

---

SETTLEMENT_FIELDS

settlement_id

workspace_id

amount

fees

tax

utr

status

settled_at

created_at

---

SETTLEMENT_PAYMENT_LINK (junction entity — required, previously
missing; without this table Settlement Gap detection in
implementation/07_RECONCILIATION_ENGINE.md cannot be implemented)

Table

razorpay_settlement_payment

Fields

settlement_payment_id (UUID PK)

workspace_id

settlement_id (FK → razorpay_settlements)

payment_id (FK → razorpay_payments)

amount_allocated (DECIMAL(18,2) — the portion of this payment
included in this settlement; a payment may rarely be split across
two settlement batches around cutoff times)

created_at

Source

Populated from Razorpay Settlement Recon API (or Settlements
report), which returns the list of payment_ids included in each
settlement UTR. Fetch during INITIAL_SYNC and every Scheduled Sync.

Constraint

UNIQUE(settlement_id, payment_id)

Validation

Reject any settlement import that does not also import its
constituent payment links. A settlement without linked payments
must not be marked ACTIVE/complete.

---

REFUND_FIELDS

refund_id

payment_id

amount

status

reason

processed_at

---

SYNC_POLICY

Hourly Scheduled

Webhook First

Retry Failed Jobs

Dead Letter Queue

Manual Retry

---

RETRY_POLICY

Maximum Attempts

5

Backoff

Exponential

Dead Letter

Enabled

---

VALIDATION

Signature Verification

Workspace Validation

Duplicate Detection

Currency Validation

Timestamp Validation

---

API

POST

/api/v1/razorpay/connect (body: key_id, key_secret, webhook_secret)

POST

/api/v1/razorpay/test-connection (validates credentials without saving)

POST

/api/v1/razorpay/disconnect

POST

/api/v1/razorpay/sync

GET

/api/v1/razorpay/status

GET

/api/v1/razorpay/payments

GET

/api/v1/razorpay/settlements

POST

/api/v1/razorpay/webhook

---

DATABASE

razorpay_connections

razorpay_payments

razorpay_orders

razorpay_refunds

razorpay_settlements

razorpay_settlement_payment

razorpay_payouts

razorpay_balance

razorpay_webhooks

razorpay_sync_jobs

audit_logs

---

EVENTS

RAZORPAY_CONNECTED

RAZORPAY_DISCONNECTED

RAZORPAY_SYNC_STARTED

RAZORPAY_SYNC_COMPLETED

RAZORPAY_SYNC_FAILED

RAZORPAY_WEBHOOK_RECEIVED

RAZORPAY_WEBHOOK_PROCESSED

RAZORPAY_TOKEN_ROTATED

PAYMENT_IMPORTED

SETTLEMENT_IMPORTED

REFUND_IMPORTED

---

ERRORS

ACCOUNT_NOT_FOUND

INVALID_SIGNATURE

INVALID_TOKEN

TOKEN_EXPIRED

ACCOUNT_ALREADY_CONNECTED

SYNC_FAILED

WEBHOOK_VALIDATION_FAILED

API_RATE_LIMIT

INVALID_SETTLEMENT

---

MONITORING

OAuth Success

OAuth Failure

Webhook Success

Webhook Failure

Payment Import Rate

Settlement Import Rate

Refund Import Rate

Sync Duration

Retry Count

API Latency

Rate Limit Usage

---

SECURITY

Verify Every Webhook Signature

Encrypt Tokens

Workspace Isolation

RBAC Required

HTTPS Only

Audit Required

Input Validation

Immutable Financial Records

---

BUSINESS_RULES

One Razorpay Account Per Workspace

Every Payment Has Unique Razorpay ID

Every Settlement References Imported Payment

Refund Cannot Exist Without Payment

Raw Payload Stored For Audit

Financial Records Never Hard Deleted

---

ACCEPTANCE

✓ OAuth Connection

✓ Token Encryption

✓ Account Verification

✓ Webhook Registration

✓ Payment Import

✓ Settlement Import

✓ Refund Import

✓ Retry Logic

✓ Disconnect

✓ Reconnect

✓ Audit Generated

---

CURSOR_RULES

Never store Razorpay credentials in plaintext.

Always verify webhook signatures.

Always process webhooks asynchronously.

Never duplicate imported payments.

Always maintain financial integrity.

Always encrypt credentials.

Always audit financial synchronization.

Always isolate records by workspace_id.

Never trust webhook payloads without verification.

Never modify imported financial records directly.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE