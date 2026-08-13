# implementation/12_SHIPPING_RECONCILIATION.md

---
document:
  id: IMP-012
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

SHIPPING_RECONCILIATION

owner:

FINANCE

---

goal:

Reconcile shipping and courier charges against what was actually
charged to the merchant, detect RTO (Return To Origin) cost leakage,
and fold shipping-related adjustments into the canonical ledger
without distorting order-level payment reconciliation
(implementation/07_RECONCILIATION_ENGINE.md).

---

WHY THIS MODULE EXISTS

Indian D2C merchants using 3PL/courier partners (Delhivery, Shiprocket,
Shadowfax, Ecom Express, Bluedart, etc.) are charged shipping fees
separately from Shopify/Razorpay — often on a weekly/fortnightly
courier invoice cycle, not per-order in real time. Forward shipping
cost, RTO cost (courier still charges for a returned/undelivered
COD shipment), and partial-RTO (partial acceptance at doorstep) are
one of the largest sources of "money leakage" merchants ask
reconciliation tools to catch. Without this module, Ganaka's
reconciliation is payment-only and misses this entirely.

---

CORE_ENTITIES

CourierConnection

CourierInvoice

CourierInvoiceLineItem

ShippingCharge

RTOEvent

PartialRTOEvent

ShippingRefund

ShippingAdjustment

CourierSettlement

---

DATA_SOURCES

Courier Partner APIs / Invoice Uploads (V1: manual CSV/Excel upload
per courier per billing cycle — matches how merchants actually
receive these today; automatic API ingestion per courier is a
scale-path item, see docs/20_SCALING_ROADMAP.md)

Shopify Order (for order-level shipping charge/method comparison)

---

COURIER_CONNECTION

fields

courier_connection_id

workspace_id

courier_name (enum: DELHIVERY, SHIPROCKET, SHADOWFAX, ECOM_EXPRESS,
BLUEDART, XPRESSBEES, OTHER)

connection_type (API or MANUAL_UPLOAD — V1 supports MANUAL_UPLOAD
only; API is out of scope for V1, do not build courier-specific API
integrations yet)

status (ACTIVE, INACTIVE)

created_at

updated_at

---

COURIER_INVOICE

fields

courier_invoice_id

workspace_id

courier_connection_id

invoice_number

invoice_date

billing_period_start

billing_period_end

total_amount

currency

file_reference (uploaded CSV/Excel, stored per docs/17_BACKUP_AND_DISASTER_RECOVERY.md
STORAGE rules)

status (UPLOADED, PARSING, PARSED, PARSE_FAILED, RECONCILED)

created_at

updated_at

---

COURIER_INVOICE_LINE_ITEM

fields

line_item_id

courier_invoice_id

workspace_id

awb_number (Air Waybill / tracking number — primary matching key
to a Shopify fulfillment)

order_reference (merchant order number as printed on the courier
invoice — secondary matching key, since AWB may not always be
captured cleanly)

charge_type (enum: FORWARD_SHIPPING, RTO, PARTIAL_RTO,
COD_HANDLING_FEE, FUEL_SURCHARGE, WEIGHT_DISCREPANCY_CHARGE,
OTHER_CHARGE)

charged_amount

expected_amount (from merchant's own shipping rate card, if
configured — see SHIPPING_RATE_CARD below; null if not configured)

weight_declared

weight_charged (courier-billed weight; frequently differs from
declared weight — this mismatch is itself a common discrepancy
type, see DISCREPANCY_TYPES below)

status (MATCHED, VARIANCE, UNMATCHED)

created_at

---

SHIPPING_RATE_CARD (optional per-workspace configuration; without
it, expected_amount comparisons are skipped and only gross invoice
totals are reconciled against Finance Engine cost entries)

fields

rate_card_id

workspace_id

courier_name

zone (enum: LOCAL, REGIONAL, NATIONAL, METRO_TO_METRO — matches
standard Indian courier zone pricing structure)

weight_slab_start

weight_slab_end

forward_rate

rto_rate

cod_handling_fee

---

RTO_EVENT

fields

rto_event_id

workspace_id

shopify_order_id

awb_number

rto_reason (enum: CUSTOMER_REFUSED, CUSTOMER_UNREACHABLE,
ADDRESS_ISSUE, COD_UNAVAILABLE, DAMAGED_IN_TRANSIT, OTHER)

rto_charge_amount (from matched COURIER_INVOICE_LINE_ITEM)

original_order_value

inventory_status (RETURNED_TO_STOCK, DAMAGED, LOST — informational,
not authoritative inventory data; Ganaka is not an inventory system
per docs/01_MASTER_CONTEXT.md OUT OF SCOPE)

created_at

---

PARTIAL_RTO_EVENT (multi-item order where some items were delivered,
some returned — common with COD orders)

fields

partial_rto_event_id

workspace_id

shopify_order_id

awb_number

delivered_line_items (array of shopify_order_item ids)

returned_line_items (array of shopify_order_item ids)

delivered_value

returned_value

rto_charge_amount

created_at

---

SHIPPING_REFUND (distinct from RULE BR-008's payment-refund
reconciliation — a shipping refund is a courier crediting back an
over-charge, not a customer-facing refund)

fields

shipping_refund_id

workspace_id

courier_invoice_line_item_id

reason (WEIGHT_DISPUTE_WON, DUPLICATE_CHARGE, SERVICE_FAILURE_CREDIT,
OTHER)

amount

status (CLAIMED, APPROVED, CREDITED, REJECTED)

created_at

---

SHIPPING_ADJUSTMENT (manual correction — e.g. merchant negotiates a
one-off discount with courier, or a dispute is settled at a
different amount than claimed)

fields

shipping_adjustment_id

workspace_id

courier_invoice_id

amount

reason (free text, required)

created_by (user_id — manual adjustments always require an actor
per RULE DB-004 audit-ownership requirement)

created_at

---

COURIER_SETTLEMENT (for COD remittance — courier collects cash from
customer, remits to merchant on a delay, net of RTO/shipping charges
— this is a THIRD money-in-transit leg distinct from Razorpay
settlements, and is exactly the leg that goes unreconciled for
COD-heavy merchants, closing the gap flagged as Critical in the
COD-blindness finding on the main reconciliation engine)

fields

courier_settlement_id

workspace_id

courier_connection_id

settlement_reference

cod_collected_amount

shipping_charges_deducted

net_remitted_amount

remitted_at

matched_shopify_order_ids (array — which COD orders this settlement
batch covers)

status (PENDING, PARTIAL, SETTLED, DISPUTED)

created_at

---

DISCREPANCY_TYPES (shipping-specific — feed the same
`reconciliation_exceptions` table used by
implementation/07_RECONCILIATION_ENGINE.md, tagged with a
`discrepancy_domain = SHIPPING` so the two exception streams stay
distinguishable in Reports/Dashboard while sharing infrastructure)

Weight Discrepancy Charge (courier billed a higher weight slab than
declared — flag if `weight_charged - weight_declared` exceeds
workspace-configurable tolerance, default 0.5kg)

Unmatched Invoice Line (AWB/order_reference on courier invoice has
no corresponding Shopify fulfillment — possible courier billing
error, or a fulfillment for a different, unconnected store)

Missing RTO Cost Recovery (Shopify order fulfillment_status =
"restocked"/order was cancelled after dispatch, but no matching
RTO charge appears on any courier invoice within the RTO
Reconciliation Window — default 30 days — meaning the courier may
owe a shipping-refund the merchant hasn't claimed)

COD Remittance Shortfall (`courier_settlement.net_remitted_amount`
does not equal `cod_collected_amount - shipping_charges_deducted`
within tolerance)

---

RECONCILIATION_PIPELINE (shipping-specific; runs independently of,
and after, implementation/07_RECONCILIATION_ENGINE.md's payment
reconciliation, since shipping invoices arrive on a different
cadence than payment/settlement data)

Upload Courier Invoice

↓

Parse Line Items

↓

Match AWB/Order Reference → Shopify Fulfillment

↓

Compare Charged vs Expected (if rate card configured)

↓

Detect Weight Discrepancy

↓

Detect RTO / Partial RTO

↓

Match COD Courier Settlements → COD Shopify Orders

↓

Generate Shipping Exceptions

↓

Post to Ledger (as FEE-type ledger entries, per
implementation/06_FINANCE_ENGINE.md LEDGER_RULES — append-only,
corrections via SHIPPING_ADJUSTMENT, never edit posted entries)

↓

Audit

---

API

POST

/api/v1/shipping/couriers (connect a courier — MANUAL_UPLOAD type
only for V1)

GET

/api/v1/shipping/couriers

POST

/api/v1/shipping/invoices (upload courier invoice file)

GET

/api/v1/shipping/invoices

GET

/api/v1/shipping/invoices/{id}

GET

/api/v1/shipping/rto

GET

/api/v1/shipping/partial-rto

GET

/api/v1/shipping/cod-settlements

POST

/api/v1/shipping/adjustments

GET

/api/v1/shipping/exceptions

GET

/api/v1/shipping/rate-card

PATCH

/api/v1/shipping/rate-card

---

DATABASE

courier_connections

courier_invoices

courier_invoice_line_items

shipping_rate_cards

rto_events

partial_rto_events

shipping_refunds

shipping_adjustments

courier_settlements

reconciliation_exceptions (shared with implementation/07, tagged
`discrepancy_domain = SHIPPING`)

audit_logs

---

EVENTS

COURIER_CONNECTED

COURIER_INVOICE_UPLOADED

COURIER_INVOICE_PARSED

COURIER_INVOICE_PARSE_FAILED

WEIGHT_DISCREPANCY_DETECTED

RTO_DETECTED

PARTIAL_RTO_DETECTED

COD_SETTLEMENT_SHORTFALL_DETECTED

SHIPPING_ADJUSTMENT_CREATED

SHIPPING_REFUND_CLAIMED

---

ERRORS

COURIER_NOT_FOUND

INVOICE_PARSE_FAILED

UNSUPPORTED_FILE_FORMAT

DUPLICATE_INVOICE

AWB_NOT_FOUND

RATE_CARD_NOT_CONFIGURED

INVALID_ADJUSTMENT_AMOUNT

---

MONITORING

Invoices Parsed

Invoices Failed

Weight Discrepancies Detected

RTO Events Detected

COD Settlement Shortfalls Detected

Average Parse Time

Unmatched Line Item Rate

---

SECURITY

Workspace Isolation

RBAC Required (finance.write for uploads/adjustments, finance.read
for viewing)

Audit Required

File Upload Validation (MIME type, extension, size — per
docs/06_SECURITY_REQUIREMENTS.md RULE SEC-013; courier invoices are
typically CSV/XLSX only, reject executable or script-bearing files)

---

BUSINESS_RULES

Shipping reconciliation is a distinct pipeline from payment
reconciliation and must never block or be blocked by it.

Courier invoice line items are immutable once matched — corrections
happen via SHIPPING_ADJUSTMENT, never by editing a parsed line item
(mirrors RULE DB-013 / BR-007's immutability principle for the
payment side).

COD Courier Settlements are a required input for full COD
reconciliation — a COD order is only considered fully reconciled
once BOTH the Shopify order is fulfilled AND a matching
courier_settlement is recorded, not merely "NOT_APPLICABLE" per
implementation/07_RECONCILIATION_ENGINE.md Step 0 (that step only
says COD orders are excluded from PAYMENT reconciliation — this
module is what actually reconciles COD money flow, closing that
gap rather than leaving COD permanently unreconciled).

Weight discrepancy tolerance and RTO Reconciliation Window are
workspace-configurable (see WORKSPACE_SETTINGS addition below),
mirroring the pattern used for reconciliation_amount_tolerance in
implementation/07_RECONCILIATION_ENGINE.md.

---

WORKSPACE_SETTINGS ADDITION

Add to implementation/02_WORKSPACE_AND_RBAC.md WORKSPACE_SETTINGS →
Reconciliation Settings:

- shipping_weight_tolerance_kg (DECIMAL, default 0.5, max 5.0)
- rto_reconciliation_window_days (INTEGER, default 30, max 90)

---

PERFORMANCE

Invoice Parse (10,000 line items)

<2 Minutes

Shipping Exception Detection (10,000 line items)

<5 Minutes

---

ACCEPTANCE

✓ Connect Courier (Manual Upload)

✓ Upload Courier Invoice

✓ Parse Invoice Line Items

✓ Match AWB To Shopify Fulfillment

✓ Detect Weight Discrepancy

✓ Detect RTO

✓ Detect Partial RTO

✓ Match COD Courier Settlements

✓ Detect COD Settlement Shortfall

✓ Manual Shipping Adjustment

✓ Post Shipping Costs To Ledger

✓ Audit Generated

---

CURSOR_RULES

Never treat a courier invoice line item as authoritative for
inventory status — Ganaka is not an inventory system, only record
what the courier reports.

Never let shipping reconciliation block or be blocked by payment
reconciliation (implementation/07) — they are independent pipelines
sharing only the `reconciliation_exceptions` table via the
`discrepancy_domain` tag.

Always post shipping charges to the ledger as append-only FEE-type
entries — never retroactively edit a posted shipping cost, only via
SHIPPING_ADJUSTMENT.

Always require an actor (`created_by`) and a reason on every manual
SHIPPING_ADJUSTMENT.

Never build automatic courier API ingestion in V1 — MANUAL_UPLOAD
only; API integrations per courier are a scale-path item
(docs/20_SCALING_ROADMAP.md), not part of this module's V1 scope.

Always isolate every table by workspace_id.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE
