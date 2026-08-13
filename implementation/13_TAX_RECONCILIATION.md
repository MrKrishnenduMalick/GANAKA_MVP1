# implementation/13_TAX_RECONCILIATION.md

---
document:
  id: IMP-013
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

TAX_RECONCILIATION

owner:

FINANCE

---

goal:

Reconcile GST (Goods and Services Tax) components recorded by
Shopify against the canonical ledger, detect tax mismatches and
rounding discrepancies, and produce accountant-facing GST summary
exports. This module does NOT file GST returns and is NOT a
statutory compliance tool — see SCOPE below.

---

SCOPE (read before implementing — prevents the AI from over-building
a tax-filing feature that was never requested)

IN SCOPE

- Recording CGST/SGST/IGST as reported by Shopify per order
- Detecting mismatches between Shopify-reported tax and
  merchant-configured expected tax rate
- Rounding-difference detection and classification
- Generating a GST Summary export for the merchant's accountant
  (implementation/09_REPORTS.md already added this as GST_SUMMARY
  format — this module is where that export's data comes from)

OUT OF SCOPE (do not build; matches docs/01_MASTER_CONTEXT.md
"Ganaka is NOT ... Tax Filing")

- GSTR-1 / GSTR-3B return generation or filing
- HSN/SAC code validation or classification
- Input Tax Credit (ITC) reconciliation
- E-way bill generation
- Any submission to the GST Network (GSTN)

Every GST-related export produced by this module must be visibly
labelled "For accountant reference only — not a GST filing document"
in the export itself, not only in this spec.

---

CORE_ENTITIES

TaxLineItem

TaxRateConfiguration

TaxMismatch

TaxRoundingAdjustment

GSTSummaryExport

---

WHY GST IS SPLIT INTO CGST / SGST / IGST

Under Indian GST law: intra-state sales split tax equally into CGST
(Central) + SGST (State); inter-state sales charge IGST (Integrated)
instead, as a single combined rate. Shopify's tax engine (or a
merchant's tax app, e.g. Quaderno) determines this per order based
on the store's registered state vs the shipping address state.
Ganaka does not recompute this determination — it only records what
Shopify reported and checks it against the merchant's own configured
expectation for detection purposes, never as an authoritative
recalculation (would risk creating a second, conflicting "source of
truth" for tax, which no merchant's accountant should trust over
their actual GST-registered billing system).

---

TAX_LINE_ITEM

fields

tax_line_item_id

workspace_id

shopify_order_id

tax_type (enum: CGST, SGST, IGST, NONE — NONE for GST-exempt or
export orders)

rate_percent (as reported by Shopify order tax_lines, e.g. 9.00 for
a 9% CGST leg of an 18% total)

taxable_value

tax_amount

source ("SHOPIFY" always for V1 — see SCOPE, Ganaka never computes
its own tax_amount from scratch)

created_at

---

TAX_RATE_CONFIGURATION (merchant-declared expectation, used only
for mismatch DETECTION, never to override Shopify's reported value)

fields

tax_rate_config_id

workspace_id

product_category (free text or Shopify product type — optional
granularity; if absent, a single workspace-default rate applies)

expected_total_rate_percent (e.g. 18.00, 12.00, 5.00, 0.00 — the
standard Indian GST slabs)

effective_from

effective_to (nullable — open-ended if still current)

created_by

created_at

---

TAX_MISMATCH

fields

tax_mismatch_id

workspace_id

shopify_order_id

expected_rate_percent (from TAX_RATE_CONFIGURATION, if configured)

actual_rate_percent (from Shopify's TAX_LINE_ITEM sum)

variance_percent

variance_amount

status (DETECTED, ACKNOWLEDGED, RESOLVED, IGNORED)

detected_at

---

TAX_ROUNDING_ADJUSTMENT (Shopify rounds tax per line item; summed
line-item tax can differ from order-level tax total by a few paise
— this is expected and must be classified separately from a real
tax mismatch, never conflated)

fields

tax_rounding_adjustment_id

workspace_id

shopify_order_id

line_item_tax_sum

order_level_tax_total

rounding_difference (always expected to be small — see
TOLERANCE below; if it exceeds tolerance, escalate as a
TAX_MISMATCH instead, not a rounding adjustment)

created_at

---

TOLERANCE

Rounding Difference Tolerance

Configurable Per Workspace

Stored In

workspace_settings.tax_rounding_tolerance

Default

0.05 (5 paise per order — standard rounding tolerance; anything
above this is a genuine mismatch, not rounding noise)

Maximum Allowed Configuration

1.00

Rate Mismatch Tolerance

Configurable Per Workspace

Stored In

workspace_settings.tax_rate_mismatch_tolerance_percent

Default

0.10 (percentage points — catches misconfigured rates like 17.9%
vs 18% due to a Shopify tax-app misconfiguration, without
flagging harmless floating-point noise)

---

DETECTION_PIPELINE

Load Canonical Financial Transaction (from
implementation/06_FINANCE_ENGINE.md — never raw Shopify import,
per that module's own BUSINESS_RULES)

↓

Sum Tax Line Items Per Order

↓

Classify Intra-State (CGST+SGST) vs Inter-State (IGST) Based On
Shopify-Reported Tax Lines (never re-derive from addresses — trust
Shopify's own classification, per SCOPE)

↓

Compare Line-Item Sum vs Order-Level Tax Total → Rounding Check

↓

If TAX_RATE_CONFIGURATION Exists For This Order's Category →
Compare Actual Rate vs Expected Rate → Mismatch Check

↓

Generate Tax Exceptions (feed `reconciliation_exceptions`, tagged
`discrepancy_domain = TAX`, same shared pattern as
implementation/12_SHIPPING_RECONCILIATION.md uses for SHIPPING)

↓

Audit

---

GST_SUMMARY_EXPORT

Fields Included

Period (date range)

Total Taxable Value

Total CGST

Total SGST

Total IGST

Order Count

Tax Mismatches Count (informational — does not affect the totals
above, which always reflect Shopify-reported figures as-is)

Rounding Adjustments Total

Generated At

Disclaimer Text (mandatory, rendered on every export — exact
wording, do not alter): "This summary is derived from Shopify's
recorded transactions and is provided for accountant reference
only. It is not a GST filing document and must not be submitted to
GSTN in place of GSTR-1/GSTR-3B."

---

API

GET

/api/v1/tax/summary

GET

/api/v1/tax/mismatches

PATCH

/api/v1/tax/mismatches/{id} (acknowledge/resolve/ignore)

GET

/api/v1/tax/rate-configurations

POST

/api/v1/tax/rate-configurations

PATCH

/api/v1/tax/rate-configurations/{id}

POST

/api/v1/tax/export (produces the GST_SUMMARY export format defined
in implementation/09_REPORTS.md)

---

DATABASE

tax_line_items

tax_rate_configurations

tax_mismatches

tax_rounding_adjustments

reconciliation_exceptions (shared, tagged `discrepancy_domain = TAX`)

audit_logs

---

EVENTS

TAX_MISMATCH_DETECTED

TAX_MISMATCH_ACKNOWLEDGED

TAX_MISMATCH_RESOLVED

TAX_ROUNDING_ADJUSTMENT_RECORDED

TAX_RATE_CONFIGURATION_CREATED

TAX_RATE_CONFIGURATION_UPDATED

GST_SUMMARY_EXPORTED

---

ERRORS

TAX_LINE_ITEM_NOT_FOUND

INVALID_TAX_RATE

RATE_CONFIGURATION_OVERLAP (two configurations for the same
category with overlapping effective date ranges — reject, require
the merchant to close out the old one first)

EXPORT_FAILED

---

MONITORING

Tax Mismatches Detected

Tax Mismatches Resolved

Rounding Adjustments Recorded

GST Summary Exports Generated

Average Detection Time

---

SECURITY

Workspace Isolation

RBAC Required (finance.read for viewing, finance.write for rate
configuration and mismatch resolution)

Audit Required

Read Only Financial Sources (this module never writes to
Shopify-sourced tax data, only to its own tax_mismatches /
tax_rounding_adjustments / tax_rate_configurations tables — mirrors
implementation/07_RECONCILIATION_ENGINE.md's "Read Only Financial
Sources" rule)

---

BUSINESS_RULES

Ganaka never recalculates or overrides Shopify's reported tax
amount — it only detects and surfaces variance against a
merchant-declared expectation.

A rounding difference within tolerance is never escalated as a tax
mismatch, and a rate variance beyond tolerance is never silently
absorbed as rounding — the two classifications are mutually
exclusive per order per DETECTION_PIPELINE above.

GST Summary exports must always carry the non-statutory disclaimer
verbatim — never omit it, never let a user configure it away.

Tax reconciliation runs independently of payment reconciliation
(implementation/07) and shipping reconciliation
(implementation/12) — three parallel, independent exception
pipelines sharing one `reconciliation_exceptions` table via the
`discrepancy_domain` tag (values: PAYMENT, SHIPPING, TAX).

---

WORKSPACE_SETTINGS ADDITION

Add to implementation/02_WORKSPACE_AND_RBAC.md WORKSPACE_SETTINGS →
Reconciliation Settings:

- tax_rounding_tolerance (DECIMAL, default 0.05, max 1.00)
- tax_rate_mismatch_tolerance_percent (DECIMAL, default 0.10, max 2.00)

---

PERFORMANCE

Tax Detection (100,000 orders)

<10 Minutes

GST Summary Export

<30 Seconds

---

ACCEPTANCE

✓ Record CGST/SGST/IGST Per Order

✓ Detect Rounding Difference

✓ Detect Rate Mismatch (when rate configuration exists)

✓ Configure Expected Tax Rate

✓ Generate GST Summary Export With Disclaimer

✓ Audit Generated

---

CURSOR_RULES

Never compute a tax amount from scratch — always use Shopify's
reported figures as the source value.

Never omit the non-statutory disclaimer from any GST-related export.

Never conflate a rounding adjustment with a tax mismatch — they use
separate tolerance settings and separate entities.

Always tag tax exceptions with `discrepancy_domain = TAX` in the
shared `reconciliation_exceptions` table.

Never build GSTR filing, HSN validation, ITC reconciliation, or
e-way bill features — explicitly out of scope, see SCOPE section.

Always isolate every table by workspace_id.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE
