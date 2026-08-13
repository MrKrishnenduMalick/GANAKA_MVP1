# implementation/09_REPORTS.md

---
document:
  id: IMP-009
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

REPORTS

owner:

PLATFORM

---

goal:

Generate canonical financial, reconciliation, operational and executive reports using only validated business data.

---

CORE_ENTITIES

Report

ReportTemplate

ReportJob

ReportExport

ReportSchedule

ReportSnapshot

ReportFilter

ReportSection

---

REPORT_TYPES

Financial Summary

Revenue Report

Settlement Report

Payment Report

Refund Report

Reconciliation Report

Ghost Order Report

Mismatch Report

Tax Report

Gateway Fee Report

Audit Report

Executive Summary

---

REPORT_STATUS

PENDING

↓

GENERATING

↓

READY

↓

EXPORTED

↓

FAILED

↓

EXPIRED

---

REPORT_PIPELINE

Validate Request

↓

Load Canonical Data

↓

Apply Filters

↓

Aggregate

↓

Generate Report

↓

Export

↓

Store Metadata

↓

Audit

---

DATA_SOURCES

Finance Engine

Reconciliation Engine

Dashboard Metrics

Audit Logs

System Metrics

---

FILTERS

Date Range

Workspace

Store

Currency

Payment Method

Order Status

Settlement Status

Transaction Type

Reconciliation Status

---

REPORT_SECTIONS

Overview

KPIs

Charts

Tables

Exceptions

Recommendations

Appendix

---

EXPORT_FORMATS

PDF

CSV

Excel

JSON

Tally XML (Tally Prime-compatible voucher import format — required
for Indian accountant workflows; map reconciled transactions to
Sales/Payment/Receipt vouchers with GST ledger split)

Zoho Books CSV (Zoho Books' documented bulk-import column format)

GST_SUMMARY (CSV — HSN-less summary of taxable value, CGST, SGST,
IGST per period, derived only from reconciled canonical records;
NOT a GSTR filing document, explicitly labelled "for accountant
reference only, not a statutory filing")

Validation

Tally XML and Zoho Books CSV exports must use the same canonical
financial records as every other report (BUSINESS_RULES below) —
never generate accounting exports from raw unreconciled imports.

---

SCHEDULES

Manual

Daily

Weekly

Monthly

Quarterly

Yearly

---

DELIVERY

Download

Email

Webhook

API

---

RETENTION

Generated Reports

90 Days

Snapshots

365 Days

Audit Logs

Permanent

---

API

GET

/api/v1/reports

POST

/api/v1/reports

GET

/api/v1/reports/{id}

DELETE

/api/v1/reports/{id}

POST

/api/v1/reports/export

POST

/api/v1/reports/schedule

PATCH

/api/v1/reports/schedule/{id}

DELETE

/api/v1/reports/schedule/{id}

GET

/api/v1/reports/download/{id}

---

DATABASE

reports

report_templates

report_jobs

report_exports

report_schedules

report_snapshots

audit_logs

---

EVENTS

REPORT_CREATED

REPORT_GENERATED

REPORT_EXPORTED

REPORT_DOWNLOADED

REPORT_DELETED

REPORT_FAILED

REPORT_SCHEDULE_CREATED

REPORT_SCHEDULE_UPDATED

REPORT_SCHEDULE_DELETED

---

ERRORS

REPORT_NOT_FOUND

INVALID_FILTER

EXPORT_FAILED

REPORT_TIMEOUT

UNSUPPORTED_FORMAT

REPORT_ALREADY_RUNNING

SCHEDULE_NOT_FOUND

---

MONITORING

Reports Generated

Reports Failed

Average Generation Time

Export Count

Download Count

Cache Hit Rate

Schedule Success Rate

---

PERFORMANCE

Summary Report

<2 Seconds

Detailed Report

<10 Seconds

Export

<30 Seconds

---

BUSINESS_RULES

Reports Use Canonical Data Only

Reports Are Read Only

Historical Reports Immutable

Exports Are Auditable

Schedules Workspace Scoped

Generated Reports Versioned

---

SECURITY

Workspace Isolation

RBAC Required

Read Only

Audit Required

HTTPS Only

Signed Download URLs

---

ACCEPTANCE

✓ Financial Reports

✓ Reconciliation Reports

✓ Executive Reports

✓ Scheduled Reports

✓ PDF Export

✓ CSV Export

✓ Excel Export

✓ JSON Export

✓ Tally XML Export

✓ Zoho Books CSV Export

✓ GST Summary Export (reference only, not a filing document)

✓ Report Download

✓ Audit Generated

---

CURSOR_RULES

Never generate reports from raw imported data.

Always use canonical financial records.

Always scope reports by workspace_id.

Always validate report filters.

Always audit report generation.

Never expose reports across workspaces.

Cache report results when possible.

Generate reports asynchronously for large datasets.

Historical reports must remain immutable.

Report exports must be reproducible.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE