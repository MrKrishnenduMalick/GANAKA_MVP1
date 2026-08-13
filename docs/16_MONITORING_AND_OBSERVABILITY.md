# 16_MONITORING_AND_OBSERVABILITY.md

---
document:
  id: DOC-016
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

MOD-MONITORING

owner:

PLATFORM

---

goal:

Observe every critical platform component.

Detect failures before customers.

Measure business health.

Provide complete auditability.

---

MONITORED_SERVICES

AUTH

API

SHOPIFY

RAZORPAY

RECON

DATABASE

REDIS

QUEUE

EMAIL

CRON

NOTIFICATION

OBJECT_STORAGE

ADMIN

---

HEALTH_STATES

HEALTHY

↓

WARNING

↓

DEGRADED

↓

OUTAGE

↓

RECOVERING

↓

HEALTHY

---

METRICS

API

requests_total

request_latency

error_rate

5xx_rate

4xx_rate

throughput

---

DATABASE

connection_count

query_latency

slow_queries

deadlocks

replication_delay

disk_usage

---

REDIS

memory

connections

hit_ratio

evictions

latency

---

QUEUE

pending_jobs

failed_jobs

retry_jobs

processing_time

worker_count

---

SHOPIFY

oauth_success

oauth_failure

sync_latency

api_limit_remaining

failed_imports

---

RAZORPAY

oauth_success

payment_sync

settlement_sync

api_errors

retry_count

---

RECONCILIATION

jobs_total

jobs_success

jobs_failed

match_rate

ghost_orders

payment_mismatch

duplicate_orders

processing_time

---

AUTH

login_success

login_failure

token_refresh

mfa_success

mfa_failure

---

BUSINESS_METRICS

new_signups

trial_started

trial_expired

active_customers

active_workspaces

daily_reconciliation

monthly_revenue

churn

conversion_rate

---

FINANCIAL_METRICS (distinct from BUSINESS_METRICS above — these
measure the correctness/health of the reconciliation product itself,
not Ganaka's own SaaS business performance)

reconciliation_match_rate (per workspace, per
implementation/07_RECONCILIATION_ENGINE.md Match Accuracy definition
— excludes NOT_APPLICABLE orders from the denominator)

ghost_orders_detected_total

missing_payments_detected_total

settlement_gaps_detected_total

refund_mismatches_detected_total

shipping_exceptions_detected_total (implementation/12_SHIPPING_RECONCILIATION.md)

tax_mismatches_detected_total (implementation/13_TAX_RECONCILIATION.md)

total_reconciled_value (sum of MATCHED transaction amounts, per
workspace, per period — the headline "money Ganaka confirmed is
correct" number merchants care about)

total_exception_value (sum of amounts currently sitting in any
unresolved exception status — the headline "money currently at risk
/ unaccounted for" number)

average_time_to_resolution (exception detected → status =
RESOLVED/ACKNOWLEDGED)

---

SLI (Service Level Indicators — how each SLO above is actually
measured; previously SLO targets were stated without their
measurement definition)

API SLI

successful_requests / total_requests, measured over 5-minute
windows, excluding requests where the client disconnected before
a response was sent (4xx client errors DO count as "successful" for
SLI purposes — they reflect the API responding correctly to a bad
request, not an API failure; only 5xx and timeouts count against
this SLI)

AUTH SLI

successful_logins / (successful_logins + failed_logins_due_to_system_error),
explicitly excluding failed_logins_due_to_invalid_credentials (a
wrong password is not a system reliability failure)

DATABASE SLI

queries_under_150ms_p95 / total_queries, measured over 5-minute
windows

RECON SLI

reconciliation_jobs_completed_within_target_time / total_reconciliation_jobs,
where target time is implementation/07_RECONCILIATION_ENGINE.md's
stated PERFORMANCE target for the given batch size

---

HYBRID_SERVICE_METRICS (Core Platform ↔ AI Service — per
docs/21_HYBRID_ARCHITECTURE.md OBSERVABILITY)

ai_service_call_duration_ms (histogram, p50/p95/p99)

ai_service_call_result (counter, labelled success/timeout/error)

ai_service_circuit_state (gauge, 0=closed/1=half-open/2=open)

ai_service_availability (derived: 1 - (open_circuit_seconds / total_seconds),
feeds a dedicated AI_SERVICE_DOWN alert distinct from the
platform-wide alerts below, since AI Service downtime degrades
rather than outright breaks the platform per docs/21's Degraded
Mode Behavior)

---

ALERTS

P1

API_DOWN

DATABASE_DOWN

AUTH_DOWN

PAYMENT_SYNC_STOPPED

---

P2

QUEUE_BACKLOG

REDIS_DOWN

HIGH_ERROR_RATE

SHOPIFY_FAILURE

RAZORPAY_FAILURE

AI_SERVICE_DEGRADED (circuit open >15 minutes — per
docs/21_HYBRID_ARCHITECTURE.md Degraded Mode Behavior)

DEAD_LETTER_QUEUE_ENTRY (per implementation/11_PLATFORM.md
EVENT_DRIVEN_ARCHITECTURE — any DLQ receiving an entry)

---

P3

HIGH_LATENCY

LOW_MATCH_RATE

FAILED_EMAILS

CACHE_MISS

SHIPPING_EXCEPTION_SPIKE (implementation/12_SHIPPING_RECONCILIATION.md)

TAX_MISMATCH_SPIKE (implementation/13_TAX_RECONCILIATION.md)

---

ALERT_RULES

API_ERROR_RATE

>

5%

5m

↓

P1

---

DATABASE_LATENCY

>

500ms

10m

↓

P2

---

QUEUE

>

1000 pending

↓

P2

---

FAILED_RECON

>

20

↓

P2

---

FAILED_LOGINS

>

100/min

↓

P2

---

SHOPIFY_SYNC_FAILURE

>

10

↓

P2

---

RAZORPAY_SYNC_FAILURE

>

10

↓

P2

---

DASHBOARDS

Platform

Authentication

API

Database

Queue

Workers

Integrations

Finance

Business

Admin

---

LOG_LEVELS

TRACE

DEBUG

INFO

WARN

ERROR

FATAL

---

STRUCTURED_LOG_FIELDS

timestamp

request_id

correlation_id

workspace_id

user_id

endpoint

latency

status

service

environment

version

ip

device

---

TRACE_PROPAGATION

request_id

↓

api

↓

service

↓

database

↓

queue

↓

worker

↓

audit

---

EVENTS

EVENT_ALERT_CREATED

EVENT_ALERT_ACKNOWLEDGED

EVENT_ALERT_RESOLVED

EVENT_HEALTH_CHANGED

EVENT_JOB_FAILED

EVENT_JOB_RETRIED

EVENT_DATABASE_FAILURE

EVENT_API_DEGRADED

---

RETENTION

metrics

180 days

logs

90 days

audit

7 years

alerts

365 days

---

SLO

API

99.9%

---

AUTH

99.95%

---

DATABASE

99.95%

---

RECON

99%

---

OBJECTIVES

API

P95

<300ms

---

DATABASE

P95

<150ms

---

RECON

10k Orders

<5 min

---

QUEUE

99%

processed

<60 sec

---

FAILURE_ACTIONS

API_DOWN

↓

restart_service

↓

notify_admin

↓

create_incident

---

DATABASE_DOWN

↓

switch_readiness

↓

alert

↓

incident

---

QUEUE_BACKLOG

↓

increase_workers

↓

retry_jobs

↓

audit

---

SECURITY_MONITORING

failed_login_spike

permission_denied_spike

jwt_validation_failure

sql_injection_attempt

xss_attempt

csrf_attempt

rate_limit_triggered

suspicious_ip

multiple_password_reset

multiple_mfa_reset

---

OBSERVABILITY_API

GET

/metrics

GET

/health

GET

/readiness

GET

/liveness

GET

/admin/metrics

GET

/admin/alerts

GET

/admin/incidents

---

BUSINESS_ALERTS

trial_expiring

subscription_failed

large_revenue_drop

abnormal_refund_rate

high_ghost_orders

high_duplicate_orders

low_reconciliation_rate

---

CURSOR_RULES

Never remove monitoring.

Never disable audit.

Never suppress critical alerts.

Every background job must expose metrics.

Every API must expose latency.

Every integration must expose health.

Every failure emits an event.

Every alert is auditable.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE