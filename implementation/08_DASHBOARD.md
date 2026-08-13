# implementation/08_DASHBOARD.md

---
document:
  id: IMP-008
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

DASHBOARD

owner:

PLATFORM

---

goal:

Provide a real-time financial operations dashboard that aggregates canonical
business data, reconciliation insights, system health and actionable alerts.

---

CORE_ENTITIES

Dashboard

Widget

KPI

Insight

Alert

Chart

Snapshot

Trend

Activity

---

DASHBOARD_TYPES

Executive

Finance

Operations

Admin

---

LAYOUT

Header

↓

Global Filters

↓

KPI Cards

↓

Financial Charts

↓

Reconciliation Summary

↓

Alerts

↓

Recent Activity

↓

System Health

---

GLOBAL_FILTERS

Workspace

Date Range

Store

Currency

Status

Payment Method

Channel

---

KPI_CARDS

Gross Revenue

Net Revenue

Orders

Payments

Settlements

Refunds

Reconciliation Rate

Ghost Orders

Failed Payments

Pending Settlements

Active Alerts

System Health

---

FINANCIAL_WIDGETS

Revenue Trend

Orders Trend

Settlement Trend

Refund Trend

Gateway Fee Trend

Tax Trend

Cash Flow Trend

Net Revenue Trend

---

RECONCILIATION_WIDGETS

Matched Transactions

Unmatched Transactions

Ghost Orders

Settlement Mismatches

Refund Mismatches

Duplicate Transactions

Manual Reviews

Daily Reconciliation Status

---

OPERATIONS_WIDGETS

Recent Imports

Running Jobs

Failed Jobs

Scheduled Jobs

Queue Size

Retry Queue

Webhook Status

API Status

---

ALERT_WIDGETS

Critical Alerts

High Alerts

Medium Alerts

Low Alerts

Resolved Alerts

Unread Alerts

---

SYSTEM_WIDGETS

CPU

Memory

Queue Health

Webhook Health

Database Health

Scheduler Health

API Health

Storage Health

---

RECENT_ACTIVITY

Imports

Connections

Reconciliation

Exports

Billing

User Actions

Security Events

---

INSIGHTS

Revenue Growth

Revenue Decline

Settlement Delay

Refund Spike

Duplicate Increase

Failed Payment Spike

Abnormal Activity

Trend Prediction

---

CHARTS

Line

Bar

Area

Pie

Donut

Table

Heatmap

---

AUTO_REFRESH

Enabled

Intervals

30 Seconds

1 Minute

5 Minutes

15 Minutes

Manual

---

CACHE_POLICY

Dashboard Cache

60 Seconds

KPI Cache

30 Seconds

Chart Cache

5 Minutes

Snapshot Cache

15 Minutes

---

API

GET

/api/v1/dashboard

GET

/api/v1/dashboard/kpis

GET

/api/v1/dashboard/charts

GET

/api/v1/dashboard/alerts

GET

/api/v1/dashboard/activity

GET

/api/v1/dashboard/system

GET

/api/v1/dashboard/insights

POST

/api/v1/dashboard/refresh

---

DATABASE

dashboard_snapshots

dashboard_widgets

dashboard_preferences

dashboard_cache

dashboard_metrics

audit_logs

---

EVENTS

DASHBOARD_VIEWED

DASHBOARD_REFRESHED

KPI_UPDATED

ALERT_CREATED

ALERT_RESOLVED

INSIGHT_GENERATED

SNAPSHOT_CREATED

WIDGET_UPDATED

---

ERRORS

DASHBOARD_NOT_AVAILABLE

CACHE_MISS

INVALID_FILTER

WIDGET_NOT_FOUND

DATA_SOURCE_UNAVAILABLE

SNAPSHOT_FAILED

---

MONITORING

Dashboard Load Time

Widget Load Time

API Latency

Refresh Count

Cache Hit Rate

Cache Miss Rate

User Sessions

Dashboard Views

---

PERFORMANCE

Dashboard Load

P95

<2 Seconds

---

KPI Load

P95

<500ms

---

Chart Load

P95

<1 Second

---

Refresh

P95

<2 Seconds

---

BUSINESS_RULES

Dashboard Uses Only Canonical Data

No Direct Reads From Raw Imports

KPIs Derived From Finance Engine

Reconciliation Metrics Derived From Reconciliation Engine

Historical Snapshots Immutable

Widgets Workspace Scoped

---

SECURITY

Workspace Isolation

RBAC Required

Read Only

Audit Required

HTTPS Only

---

ACCEPTANCE

✓ KPI Dashboard

✓ Financial Charts

✓ Reconciliation Summary

✓ Alert Center

✓ Recent Activity

✓ System Health

✓ Auto Refresh

✓ Dashboard Filters

✓ Dashboard Preferences

✓ Audit Generated

---

CURSOR_RULES

Never calculate KPIs from raw source data.

Always use canonical financial records.

Always scope dashboard data by workspace_id.

Always cache expensive queries.

Never expose internal system metrics to unauthorized roles.

Every dashboard request must respect RBAC.

Every dashboard interaction must be auditable.

Dashboard must degrade gracefully when a widget fails.

Widgets load independently.

Dashboard must remain functional even if one service is unavailable.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE