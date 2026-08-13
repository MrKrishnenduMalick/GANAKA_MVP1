# implementation/07_RECONCILIATION_ENGINE.md

---
document:
  id: IMP-007
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

RECONCILIATION_ENGINE

owner:

PLATFORM

---

goal:

Automatically reconcile Shopify commerce data with Razorpay payment and
settlement data, detect financial discrepancies, generate actionable
insights and maintain a complete audit trail.

---

CORE_ENTITIES

ReconciliationJob

ReconciliationResult

MatchedTransaction

Mismatch

GhostOrder

MissingPayment

DuplicatePayment

SettlementGap

RefundMismatch

Anomaly

Exception

---

DATA_INPUTS

Shopify Orders

Shopify Refunds

Shopify Customers

Razorpay Payments

Razorpay Orders

Razorpay Settlements

Razorpay Refunds

Finance Ledger

---

JOB_STATUS

PENDING

↓

RUNNING

↓

MATCHING

↓

VALIDATING

↓

REPORTING

↓

COMPLETED

↓

FAILED

---

MATCH_STATUS

NOT_APPLICABLE (non-Razorpay gateway order, e.g. COD — excluded from
reconciliation, not an error, see DISCREPANCY DECISION TABLE Step 0)

MATCHED

PARTIAL_MATCH

UNMATCHED

MISSING_PAYMENT

MISSING_ORDER

DUPLICATE

REFUND_MISMATCH

REFUNDED (order + refund matched cleanly within tolerance on both
sides — distinct from REFUND_MISMATCH, which is an exception state;
see docs/22_FINANCIAL_EDGE_CASES.md RULE BR-021)

SETTLEMENT_MISMATCH

MANUAL_REVIEW

---

MATCHING_PRIORITY

1

Shopify Order ID

↓

2

Razorpay Order ID

↓

3

Payment Reference

↓

4

Gateway Reference

↓

5

Amount + Timestamp

---

MATCHING_RULES

Exact Amount

Currency Match

Reference Match

Settlement Match

Refund Validation

Duplicate Detection

Timezone Normalization

Tolerance Validation

---

DISCREPANCY_TYPES

Ghost Order

Payment Missing

Settlement Missing

Duplicate Payment

Duplicate Order

Refund Difference

Cancelled Order Not Refunded (order cancelled after payment capture,
no refund appears within settlement_match_window_days — a more
urgent framing than a generic Refund Difference since the merchant
is holding customer money on a dead order; see
docs/22_FINANCIAL_EDGE_CASES.md RULE BR-032)

Settlement Difference

Tax Difference (see implementation/13_TAX_RECONCILIATION.md for the
dedicated tax reconciliation pipeline — this entry covers only
payment-side tax discrepancies discovered incidentally during
matching, not the primary tax detection path)

Gateway Fee Difference

Unexpected Adjustment

---

RECONCILIATION_PIPELINE

Load Canonical Records

↓

Validate Records

↓

Index References

↓

Match Orders

↓

Match Payments

↓

Match Settlements

↓

Detect Exceptions

↓

Generate Report

↓

Persist Results

↓

Audit

---

TOLERANCE_RULES

Currency

Exact

---

Amount

Configurable Per Workspace

Stored In

workspace_settings.reconciliation_amount_tolerance

Default

0.00

Maximum Allowed Configuration

5.00

---

Timestamp (Webhook/Duplicate Dedup Window)

5 Minutes

---

Settlement Match Window (Order Payment Date → Settlement Date)

Configurable Per Workspace

Stored In

workspace_settings.settlement_match_window_days

Default

15 Days

Maximum Allowed Configuration

45 Days

Reason

Razorpay settlements routinely lag payment capture by several
business days (T+2 typical, longer around bank holidays). A 5-minute
window is only valid for webhook-duplicate detection, never for
order-to-settlement matching.

---

# AI_SERVICE_DELEGATION

The DISCREPANCY DECISION TABLE below defines WHAT the matching logic
must do. It does not by itself say WHERE it runs. Per
docs/21_HYBRID_ARCHITECTURE.md (authoritative for this split):

- Core Platform Service (Spring Boot) owns: creating reconciliation
  jobs, loading canonical records, calling the AI Service, persisting
  `reconciliation_results`/`reconciliation_exceptions`, serving the
  reconciliation APIs below, and everything under RECONCILIATION_PIPELINE
  up to and including "Load Canonical Records" / "Index References".
- AI Service (FastAPI) owns: executing the DISCREPANCY DECISION TABLE
  itself (Steps 0-5, MATCH_STATUS RESOLUTION ORDER) and returning
  match_status + confidence per order, via the internal API defined
  in docs/21_HYBRID_ARCHITECTURE.md COMMUNICATION.

This decision table is therefore the CONTRACT between the two
services, not solely an internal Core Platform algorithm. Any change
to it requires updating both services' implementations together —
treat it like a versioned API contract (see docs/21's `model_version`
requirement).

---

# DISCREPANCY DECISION TABLE

This section is authoritative and MUST be implemented exactly as
written. Do not infer alternative thresholds. If a scenario is not
covered here, STOP per AI_CONSTITUTION Article 11 and request
clarification instead of inventing a rule.

---

## STEP 0 — GATEWAY ELIGIBILITY FILTER (runs before any matching)

Rule

Every Shopify order carries a `payment_gateway_names` array
(see implementation/04_SHOPIFY.md ORDER_FIELDS).

If

`payment_gateway_names` does NOT contain a Razorpay-family gateway
(e.g. contains only "Cash on Delivery (COD)", "Manual Payment",
"Bank Transfer", or any gateway other than Razorpay)

Then

Assign MATCH_STATUS = NOT_APPLICABLE.

Do NOT evaluate this order for Ghost Order / Missing Payment.

Exclude it from Match Accuracy and reconciliation-rate KPI denominators.

Still show it in Dashboard "Non-Reconcilable Orders" widget for visibility.

Validation

Reject any implementation that raises a payment/reconciliation
exception for a non-Razorpay-gateway order.

---

## STEP 1 — GHOST ORDER

Definition

A Shopify order where `payment_gateway_names` contains a Razorpay
gateway, AND `financial_status` = "paid", AND no Razorpay Payment
record exists with matching `order_id`/`notes.shopify_order_id`
reference after Settlement Match Window (default 15 days) has
elapsed since `order.created_at`.

Trigger Condition

```
order.financial_status == "paid"
AND order.payment_gateway_names includes razorpay
AND no matching razorpay_payments found
AND now() - order.created_at > settlement_match_window_days
```

Before Window Elapses

Status = PENDING_MATCH (not yet an exception). Do not notify.

After Window Elapses

Status = GHOST_ORDER. Raise GHOST_ORDER_DETECTED event. Requires
manual review.

---

## STEP 2 — MISSING PAYMENT

Definition

Distinct from Ghost Order: a Razorpay Order (`razorpay_order_id`)
exists (merchant initiated Razorpay checkout) but no corresponding
`razorpay_payments` with status `captured` exists for it, after
1 hour has elapsed (covers async payment methods e.g. UPI collect,
netbanking redirects).

Trigger Condition

```
razorpay_orders exists
AND no razorpay_payments.status == "captured" linked to it
AND now() - razorpay_orders.created_at > 1 hour
```

---

## STEP 3 — DUPLICATE PAYMENT

Definition

Two or more `razorpay_payments` records with `status = captured`
reference the same `shopify_order_id`.

Trigger Condition

```
count(razorpay_payments WHERE status = captured
      AND shopify_order_id = X) > 1
```

Action

Flag all but the earliest-captured payment as DUPLICATE. Never
auto-refund. Always route to manual review.

---

## STEP 4 — SETTLEMENT GAP

Definition

A `razorpay_payments` with `status = captured` has no corresponding
row in `razorpay_settlement_payment` (see implementation/05_RAZORPAY.md)
after Settlement Match Window (default 15 days) has elapsed since
`captured_at`.

Trigger Condition

```
payment.status == "captured"
AND no razorpay_settlement_payment row references payment.id
AND now() - payment.captured_at > settlement_match_window_days
```

---

## STEP 5 — REFUND MISMATCH

Definition

Sum of `shopify_refunds.amount` for an order does not equal sum of
`razorpay_refunds.amount` for the linked payment(s), evaluated only
after both sides report the refund as processed/completed. Compare
using amount tolerance (default 0.00, configurable).

Trigger Condition

```
abs(sum(shopify_refunds.amount for order)
    - sum(razorpay_refunds.amount for linked payment))
  > workspace.reconciliation_amount_tolerance
```

---

## MATCH_STATUS RESOLUTION ORDER

Evaluate in this exact order per order; first matching status wins,
do not evaluate subsequent steps once assigned:

```
1. NOT_APPLICABLE      (Step 0 gateway filter)
2. DUPLICATE           (Step 3)
3. MATCHED             (exact amount + reference + settled)
4. PARTIAL_MATCH       (matched payment, refund/settlement pending)
5. MISSING_PAYMENT     (Step 2)
6. GHOST_ORDER         (Step 1)
7. SETTLEMENT_MISMATCH (Step 4)
8. REFUND_MISMATCH     (Step 5)
9. MANUAL_REVIEW       (anything not resolved above within 2x the
                        Settlement Match Window)
```

---

MATCH_OUTPUT

Matched Count

Partial Matches

Ghost Orders

Duplicate Orders

Missing Payments

Refund Issues

Settlement Issues

Success Rate

Confidence Score

---

REPORTS

Daily Summary

Weekly Summary

Monthly Summary

Mismatch Report

Settlement Report

Refund Report

Executive Summary

---

AUTOMATION

Nightly Reconciliation

Manual Reconciliation

Scheduled Retry

Automatic Retry

Dead Letter Queue

---

MANUAL_ACTIONS

Ignore Exception

Resolve Exception

Retry Match

Merge Records

Export Exception

Assign Review

---

API

POST

/api/v1/reconciliation/run

GET

/api/v1/reconciliation/jobs

GET

/api/v1/reconciliation/results

GET

/api/v1/reconciliation/exceptions

POST

/api/v1/reconciliation/retry

POST

/api/v1/reconciliation/resolve

GET

/api/v1/reconciliation/report

POST

/api/v1/reconciliation/export

---

DATABASE

reconciliation_jobs

reconciliation_results

reconciliation_matches

reconciliation_exceptions

reconciliation_reports

reconciliation_statistics

manual_reviews

audit_logs

---

EVENTS

RECONCILIATION_STARTED

RECONCILIATION_COMPLETED

RECONCILIATION_FAILED

MATCH_CREATED

MISMATCH_DETECTED

GHOST_ORDER_DETECTED

SETTLEMENT_MISMATCH_DETECTED

REFUND_MISMATCH_DETECTED

MANUAL_REVIEW_REQUIRED

REPORT_GENERATED

---

ERRORS

MATCH_FAILED

INVALID_REFERENCE

MISSING_PAYMENT

MISSING_ORDER

SETTLEMENT_NOT_FOUND

REFUND_NOT_FOUND

DUPLICATE_REFERENCE

INVALID_CURRENCY

RECONCILIATION_TIMEOUT

---

MONITORING

Jobs Completed

Jobs Failed

Average Runtime

Match Rate

Mismatch Count

Ghost Orders

Settlement Gaps

Refund Issues

Retry Count

Manual Reviews

---

SECURITY

Workspace Isolation

Audit Required

RBAC Required

Immutable Results

Read Only Financial Sources

Encrypted Configuration

---

BUSINESS_RULES

One Canonical Match Per Transaction

One Payment Cannot Match Multiple Orders

One Settlement Cannot Be Counted Twice

Refund Must Reference Existing Payment

Duplicate Detection Runs Before Matching

Reconciliation Never Modifies Source Records

Manual Resolution Never Changes Imported Data

Every Exception Is Traceable

Every Run Is Auditable

---

PERFORMANCE

100000 Transactions

<10 Minutes

---

Match Accuracy

>99.9%

Measured Over

Orders with MATCH_STATUS != NOT_APPLICABLE only (i.e. Razorpay-gateway
orders). NOT_APPLICABLE orders (COD, manual, other gateways) are
excluded from this metric's denominator — see DISCREPANCY DECISION
TABLE Step 0.

---

Dashboard Availability

<30 Seconds

---

Report Generation

<60 Seconds

---

ACCEPTANCE

✓ Match Shopify Orders

✓ Match Razorpay Payments

✓ Match Settlements

✓ Detect Ghost Orders

✓ Detect Missing Payments

✓ Detect Refund Mismatches

✓ Detect Duplicate Transactions

✓ Generate Reports

✓ Export Results

✓ Manual Review Queue

✓ Audit Generated

---

CURSOR_RULES

Never modify imported Shopify records.

Never modify imported Razorpay records.

Always reconcile against canonical financial records.

Always use deterministic matching order.

Always deduplicate before reconciliation.

Never silently ignore mismatches.

Every mismatch must have a reason code.

Every reconciliation run must be reproducible.

Every reconciliation result must be immutable.

Every reconciliation action must be audited.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE