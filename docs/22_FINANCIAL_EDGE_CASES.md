# 22_FINANCIAL_EDGE_CASES.md

# Ganaka Financial Edge Cases

Version: 1.0.0

Status: Approved

---

# PURPOSE

docs/07_BUSINESS_RULES.md defines the general business rules. This
document defines EDGE CASES — the specific, often-ambiguous
scenarios that a generic rule doesn't fully resolve on its own, and
that would otherwise be left for the AI to guess. Every rule here is
additive to, and must never contradict, docs/07_BUSINESS_RULES.md.
Numbering continues from BR-020 as BR-021 onward, in the same
document family, to make cross-referencing unambiguous.

---

# RULE BR-021 — REFUND (SINGLE, FULL)

Scenario

A single Razorpay payment is refunded in full, matching the full
Shopify order refund.

Rule

Reconciled independently per BR-008. Ledger posts one REFUND entry
equal to the payment amount. Order's MATCH_STATUS transitions from
MATCHED to REFUNDED (add this status if not already present in
implementation/07_RECONCILIATION_ENGINE.md's MATCH_STATUS enum —
it is distinct from REFUND_MISMATCH, which only applies when the
Shopify-side and Razorpay-side refund amounts disagree).

---

# RULE BR-022 — PARTIAL REFUND

Scenario

Shopify order is partially refunded (e.g. one item out of three).

Rule

Razorpay refund amount is expected to equal the Shopify partial
refund amount, within `reconciliation_amount_tolerance`
(implementation/07_RECONCILIATION_ENGINE.md TOLERANCE_RULES). A
partial refund does NOT change the order's underlying MATCHED
status for the un-refunded portion — only the refunded portion is
evaluated against RULE BR-021/REFUND_MISMATCH logic. Never treat a
partial refund as a full order match failure.

---

# RULE BR-023 — MULTIPLE REFUNDS ON ONE ORDER

Scenario

An order receives more than one refund over time (e.g. one item
refunded this week, another item refunded next week).

Rule

Each Shopify refund event and each Razorpay refund event are
recorded as separate, individually-auditable ledger entries (never
merged into one running total that loses the individual events).
Reconciliation compares the SUM of all refunds on each side, not
just the most recent one, against the tolerance. A mismatch is
raised against the cumulative totals, and the mismatch record must
list which individual refund events were included in the comparison
(traceability requirement — ties to Article 13 AUDITABILITY).

---

# RULE BR-024 — CHARGEBACK

Scenario

Customer disputes a card payment with their bank; Razorpay reports
a chargeback (distinct from a merchant-initiated refund).

Rule

Chargebacks are their own TRANSACTION_TYPE (already listed in
implementation/06_FINANCE_ENGINE.md TRANSACTION_TYPES as
`CHARGEBACK`) and must never be recorded as a REFUND — a chargeback
is bank-initiated and typically carries an additional dispute fee,
which a refund does not. A chargeback:

- Posts a negative ledger entry for the disputed amount PLUS any
  dispute fee reported by Razorpay, as two separate line items.
- Triggers a CRITICAL-priority notification
  (implementation/10_NOTIFICATION_SYSTEM.md) — chargebacks need
  faster human attention than a routine refund.
- Does not automatically alter the Shopify order's fulfillment or
  refund status — Ganaka only reflects the financial event; the
  merchant decides whether to also action the order in Shopify.

---

# RULE BR-025 — PAYMENT FAILURE

Scenario

Razorpay reports `payment.failed` for a checkout attempt.

Rule

A failed payment attempt is recorded (for visibility/analytics —
feeds implementation/08_DASHBOARD.md "Failed Payments" KPI) but is
NEVER treated as a financial transaction requiring reconciliation —
it has no settled money. If the corresponding Shopify order later
shows `financial_status = pending` or is cancelled, no
GHOST_ORDER/MISSING_PAYMENT exception is raised for it (the order
was never expected to have a captured payment). If the customer
successfully retries and a later `payment.captured` event links to
the same Shopify order, normal matching applies to that later
payment only.

---

# RULE BR-026 — DUPLICATE PAYMENT (CUSTOMER-SIDE)

Scenario

Customer's card is charged twice for the same order (e.g. a retry
after a slow/ambiguous gateway response created two successful
captures).

Rule

Already covered structurally by
implementation/07_RECONCILIATION_ENGINE.md DISCREPANCY DECISION
TABLE Step 3 (DUPLICATE). This rule clarifies handling: Ganaka
flags the duplicate for manual review and NEVER auto-initiates a
refund of the extra payment (per BR/CURSOR_RULES pattern: reconciliation
never takes financial action, only detects and surfaces — refunding
the duplicate is the merchant's action, taken in Razorpay directly,
which Ganaka then picks up as a normal REFUND event once it happens).

---

# RULE BR-027 — SETTLEMENT DELAY

Scenario

A captured payment has not appeared in any settlement after the
configured `settlement_match_window_days` (default 15 — see
implementation/07_RECONCILIATION_ENGINE.md).

Rule

Already covered as SETTLEMENT_MISMATCH (Step 4). This rule adds:
distinguish a delay (settlement will likely still arrive) from a
permanent gap (settlement will never arrive, e.g. account
suspended) by re-checking at 2x and 4x the window before escalating
notification priority from MEDIUM → HIGH → CRITICAL. Never let a
single delayed settlement generate three separate duplicate
notifications for the same underlying event — escalate the
existing notification's priority in place (ties to
implementation/10_NOTIFICATION_SYSTEM.md "Duplicate Notifications
Are Prevented").

---

# RULE BR-028 — SETTLEMENT SPLIT

Scenario

A single Razorpay payment's amount is settled across two separate
settlement batches (rare, but occurs around bank cut-off times or
partial holds).

Rule

This is exactly why `razorpay_settlement_payment.amount_allocated`
exists (implementation/05_RAZORPAY.md SETTLEMENT_PAYMENT_LINK) as a
per-link amount rather than assuming a payment maps 1:1 to a
settlement. A payment is only considered fully settled once the
SUM of `amount_allocated` across all its settlement links equals
the payment amount (within tolerance) — not merely once ANY
settlement link exists for it.

---

# RULE BR-029 — GATEWAY FEE

Scenario

Razorpay deducts its transaction fee (+ GST on that fee) before
settling.

Rule

Gateway fee is recorded as its own ledger entry (TRANSACTION_TYPE =
`FEE`, already defined in implementation/06_FINANCE_ENGINE.md),
linked to the originating payment, never netted silently into the
settlement amount without a visible line item. Net Revenue
calculations (implementation/06_FINANCE_ENGINE.md
FINANCIAL_CALCULATIONS) must subtract Gateway Fee explicitly, and
the fee's own GST component (Razorpay charges GST on its fees) is
recorded as a TAX-type ledger entry distinct from the merchant's
own sales tax handled in implementation/13_TAX_RECONCILIATION.md —
never conflate the two.

---

# RULE BR-030 — PLATFORM FEE / COMMISSION

Scenario

Ganaka's own subscription fee (docs/13_BILLING_AND_SUBSCRIPTIONS.md),
or, if a future marketplace/commission model is introduced, a
per-transaction commission.

Rule

Ganaka's own billing is entirely separate from a merchant's
reconciled financial ledger — never post Ganaka's subscription fee
as a ledger entry inside a workspace's financial reconciliation
data. They are different domains (docs/13 vs
implementation/06_FINANCE_ENGINE.md) and must never share a table
or be summed together in any report.

---

# RULE BR-031 — CASH ON DELIVERY (COD)

Scenario

Order paid in cash at delivery, collected by courier, remitted to
merchant later.

Rule

Excluded from Razorpay payment reconciliation entirely per
implementation/07_RECONCILIATION_ENGINE.md Step 0
(`MATCH_STATUS = NOT_APPLICABLE`). Reconciled instead through the
courier settlement flow defined in
implementation/12_SHIPPING_RECONCILIATION.md COURIER_SETTLEMENT — a
COD order's financial reconciliation is only complete once a
matching `courier_settlement.matched_shopify_order_ids` entry
exists for it. Never mark a COD order "reconciled" based on
Shopify fulfillment status alone.

---

# RULE BR-032 — CANCELLED ORDERS

Scenario

Order cancelled before or after payment capture.

Rule

Cancelled before capture: no financial transaction exists, nothing
to reconcile (mirrors BR-025 payment-failure handling).

Cancelled after capture, before fulfillment: expect a refund
(BR-021/022) — if no refund appears within
`settlement_match_window_days`, raise a distinct exception type
`CANCELLED_ORDER_NOT_REFUNDED` (add to
implementation/07_RECONCILIATION_ENGINE.md DISCREPANCY_TYPES) rather
than silently classifying it as a generic REFUND_MISMATCH — a
merchant needs to know specifically that they're holding customer
money on a cancelled order, which is a more urgent framing than a
generic mismatch.

Cancelled after fulfillment: treated as a return; if COD, apply
BR-031's courier-settlement path (courier may have already
attempted RTO); if prepaid, apply BR-021/022.

---

# RULE BR-033 — EXCHANGE ORDERS

Scenario

Customer exchanges an item — Shopify may model this as a new order
linked to the original, or as an edit to the existing order
(varies by merchant's exchange app/workflow).

Rule

Ganaka does not attempt to infer exchange linkage automatically in
V1 (no reliable, universal Shopify data model for "this order is an
exchange of that order" across the many exchange apps merchants
use — attempting to guess would violate Article 11 NO GUESSING).
Each resulting Shopify order/order-edit is reconciled independently
per its own financial events. A future version MAY add explicit
exchange-app integrations (e.g. Return Prime, ClickPost) as a
scale-path item — do not build speculative exchange-linkage logic
now.

---

# RULE BR-034 — GIFT CARDS

Scenario

Order paid partially or fully with a Shopify gift card.

Rule

The gift-card-covered portion of an order total has no
corresponding Razorpay payment — it is Shopify-internal. When
computing expected Razorpay payment amount for matching purposes
(implementation/07_RECONCILIATION_ENGINE.md), always use
`order.total - gift_card_amount_used`, never `order.total` alone.
implementation/04_SHOPIFY.md ORDER_FIELDS must capture
`gift_card_amount_used` as a field (add it) so this subtraction is
possible without a second API call per order.

Add to implementation/04_SHOPIFY.md ORDER_FIELDS:

- gift_card_amount_used (DECIMAL, default 0.00)

---

# RULE BR-035 — STORE CREDIT

Scenario

Refund issued as store credit instead of an original-payment-method
refund.

Rule

A store-credit refund does NOT create a corresponding Razorpay
refund — the money was never returned via the gateway. Ganaka must
recognize `shopify_refunds` records where the refund's transaction
type indicates store credit (Shopify's refund object exposes this)
and exclude them from BR-021/022 Razorpay-refund matching entirely
— they are not a REFUND_MISMATCH candidate at all, they are their
own category. Add `refund_method` (enum: ORIGINAL_PAYMENT,
STORE_CREDIT, MANUAL) to implementation/04_SHOPIFY.md's shopify_refunds
fields, and only route `ORIGINAL_PAYMENT` refunds into Razorpay
refund matching.

---

# RULE BR-036 — MANUAL ADJUSTMENT

Scenario

Merchant or accountant needs to correct the ledger for a reason
Ganaka has no automated source for (e.g. a negotiated partial waiver
with a customer, an accounting correction).

Rule

Already structurally supported via
implementation/06_FINANCE_ENGINE.md's `Adjustment` entity and
LEDGER_RULES ("Correction By Adjustment Entry"). This rule adds:
every manual adjustment MUST carry a non-empty free-text reason and
a `created_by` actor (mirrors implementation/12's
SHIPPING_ADJUSTMENT pattern), must never directly edit a posted
ledger entry, and must be visually distinguished in Reports (a
"Manual" badge/column) so an accountant reviewing a report can
always tell system-derived figures from human-entered ones apart at
a glance.

---

# RULE BR-037 — CURRENCY ROUNDING

Scenario

Small rounding differences between Shopify-reported and
Razorpay-reported amounts for the same logical transaction (paise-level
differences, not tax-specific — see
implementation/13_TAX_RECONCILIATION.md for tax-specific rounding).

Rule

Use the SAME `reconciliation_amount_tolerance` setting
(implementation/07_RECONCILIATION_ENGINE.md TOLERANCE_RULES,
default 0.00) for currency rounding as for general amount matching
— do not introduce a second, separate rounding-tolerance concept for
payments (implementation/13's tax rounding tolerance is intentionally
separate and only applies to tax line items, not general
payment/order amounts — do not merge the two settings).

---

# REFERENCES

Business Rules

docs/07_BUSINESS_RULES.md

Reconciliation Engine

implementation/07_RECONCILIATION_ENGINE.md

Shipping Reconciliation

implementation/12_SHIPPING_RECONCILIATION.md

Tax Reconciliation

implementation/13_TAX_RECONCILIATION.md

Finance Engine

implementation/06_FINANCE_ENGINE.md

---

END OF DOCUMENT
