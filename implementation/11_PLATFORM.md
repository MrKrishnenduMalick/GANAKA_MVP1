# implementation/11_PLATFORM.md

---
document:
  id: IMP-011
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

PLATFORM

owner:

ENGINEERING

---

goal:

Provide the shared platform infrastructure powering every Ganaka module,
including background jobs, caching, storage, feature flags, configuration,
observability, scheduling and internal platform services.

---

CORE_ENTITIES

PlatformConfiguration

FeatureFlag

Job

Queue

Scheduler

Cache

StorageObject

Secret

AuditEvent

HealthCheck

SystemService

---

PLATFORM_SERVICES

Authentication

Authorization

Configuration

Scheduler

Queue

Cache

Storage

Email

Logging

Monitoring

Audit

Billing

Notification

---

SERVICE_STATUS

HEALTHY

↓

DEGRADED

↓

UNAVAILABLE

↓

MAINTENANCE

---

CONFIGURATION

Environment Variables

Secrets

Runtime Configuration

Feature Flags

Tenant Configuration

System Defaults

---

FEATURE_FLAGS

Enabled

Disabled

Percentage Rollout

Workspace Rollout

Role Rollout

Environment Rollout

---

QUEUE_TYPES

Import Queue

Reconciliation Queue

Notification Queue

Report Queue

Billing Queue

Audit Queue

Cleanup Queue

Webhook Queue

---

JOB_STATUS

QUEUED

↓

RUNNING

↓

RETRYING

↓

COMPLETED

↓

FAILED

↓

DEAD_LETTER

---

SCHEDULERS

Hourly Sync

Nightly Reconciliation

Daily Reports

Daily Backup

Cleanup

Subscription Renewal

Trial Expiration

Health Check

---

# EVENT_DRIVEN_ARCHITECTURE

Each QUEUE_TYPE above is a Redis Stream (implementation/00_FOUNDATION.md
TECH_STACK). This section defines the consumer/retry/ordering/dedup
contract every queue must follow — previously each module referenced
"Queue Processing" without a shared, concrete contract; this closes
that gap once, here, rather than repeating it per module.

CONSUMERS (one consumer group per queue, one logical consumer type
per group — never share a consumer group across unrelated queues)

Import Queue → ImportWorker (Shopify/Razorpay/Courier import jobs)

Reconciliation Queue → ReconciliationWorker (calls AI Service per
docs/21_HYBRID_ARCHITECTURE.md, persists results)

Notification Queue → NotificationWorker (implementation/10_NOTIFICATION_SYSTEM.md)

Report Queue → ReportWorker (implementation/09_REPORTS.md)

Billing Queue → BillingWorker (docs/13_BILLING_AND_SUBSCRIPTIONS.md)

Audit Queue → AuditWorker (write-only, never blocks the originating
request — audit writes are always async per RULE DB rules)

Cleanup Queue → CleanupWorker (soft-delete purge, expired export
cleanup)

Webhook Queue → WebhookWorker (post-signature-verification processing
only — signature verification itself, per RULE SEC-021, happens
synchronously in the receiving HTTP handler before enqueueing, never
inside the async worker, so an invalid signature never even enters
a queue)

RETRY POLICY (per queue, overridable per job type where a module
doc already specifies a different value — e.g.
implementation/15_CUSTOMER_ONBOARDING's own FAILURE RECOVERY retry
counts take precedence for onboarding-specific jobs)

Default

3 attempts, exponential backoff (5s, 25s, 125s)

Reconciliation Queue

5 attempts, exponential backoff (10s, 30s, 90s, 270s, 810s) — matches
implementation/07_RECONCILIATION_ENGINE.md RETRY_POLICY

Webhook Queue

5 attempts, exponential backoff (matches provider redelivery
windows — Shopify/Razorpay both retry webhooks themselves for up
to 48 hours, so Ganaka's own internal retry only needs to cover
transient internal failures, not provider-side ones)

DEAD LETTER QUEUE

After retry exhaustion, a job moves to `DEAD_LETTER` status (already
defined in JOB_STATUS above) and is written to a dedicated
`{queue_name}_dlq` Redis Stream, never silently dropped. A CRITICAL
alert (docs/16_MONITORING_AND_OBSERVABILITY.md) fires when any DLQ
receives an entry. DLQ entries require manual admin review
(docs/14_ADMIN_OPERATIONS.md) and manual replay via an explicit
"Replay Dead Letter Job" admin action — never auto-replayed, since
repeated automatic replay of a permanently-failing job is itself a
failure mode (thundering herd against a downstream dependency that
is down for a real reason).

ORDERING

Redis Streams preserve per-partition (per-stream) order. Jobs that
must be processed in order for the same entity (e.g. two webhook
events for the same shopify_order_id) are published to the same
stream partition keyed by `workspace_id` (not by entity id) — this
guarantees ordering is preserved at least at the workspace level,
which is sufficient because cross-workspace ordering is never a
correctness requirement (tenant isolation means workspaces never
have ordering dependencies on each other). Within a workspace,
strict per-entity ordering is additionally enforced by the
consumer re-checking the entity's `updated_at`/version before
applying a stale event — never assume queue order alone is
sufficient for correctness on a single entity if two events for it
could theoretically be processed by different consumer instances.

DUPLICATE DETECTION

Every event carries a unique `event_id`. Consumers check
`processed_events` (Redis, TTL 7 days, same mechanism as
docs/06_SECURITY_REQUIREMENTS.md RULE SEC-022's webhook dedup) before
processing, and record it after successful processing — this makes
every consumer idempotent against at-least-once delivery semantics,
which Redis Streams provide (not exactly-once).

FAILURE RECOVERY

If a worker crashes mid-processing, its claimed-but-unacknowledged
messages are reclaimed by another consumer in the same group after
a 60-second claim-idle timeout (Redis Streams `XCLAIM` /
XAUTOCLAIM pattern), then reprocessed — idempotency (above) ensures
this is safe even if the original worker had partially completed
the work before crashing.

---

# BACKGROUND_JOBS

CRON SCHEDULE (concrete times, previously only named, not scheduled)

Hourly Sync — every hour, minute 0

Nightly Reconciliation — daily, 02:00 IST (chosen to run after most
settlement/webhook activity for the day has settled, before business
hours)

Daily Reports — daily, 04:00 IST

Daily Backup — daily, 01:00 IST (per docs/17_BACKUP_AND_DISASTER_RECOVERY.md)

Cleanup — daily, 03:00 IST

Subscription Renewal — daily, 00:30 IST

Trial Expiration — daily, 00:15 IST

Health Check — every 60 seconds

TIMEOUT (per job type; a job exceeding this is killed and moved to
FAILED → normal RETRY POLICY applies)

Hourly Sync

10 minutes

Nightly Reconciliation

2 hours (matches implementation/07_RECONCILIATION_ENGINE.md
PERFORMANCE target of <10 minutes per 100,000 transactions, scaled
up with margin for the largest expected workspace)

Daily Reports

30 minutes

Daily Backup

1 hour

Cleanup

30 minutes

CONCURRENCY

Each worker type runs with a configurable pool size (environment
variable, default 5 concurrent jobs per worker instance). Jobs for
the SAME workspace_id never run concurrently within a job type
(enforced via DISTRIBUTED LOCKING below) — prevents, for example,
two overlapping reconciliation runs for one workspace corrupting
shared intermediate state. Jobs for DIFFERENT workspaces always may
run concurrently — concurrency limits are per-worker-instance
capacity, never an artificial cross-tenant serialization.

WORKER OWNERSHIP

Each queue has exactly one owning worker type (see CONSUMERS above)
— never two different worker types competing for the same queue,
which would break the ordering/idempotency guarantees above. Worker
processes are stateless and horizontally scalable; scaling a worker
type means running more instances of the same consumer group
member, never introducing a second, differently-behaved consumer.

DISTRIBUTED LOCKING

Implemented via Redis (`SET key value NX PX <ttl>` pattern, e.g.
Redisson's distributed lock or equivalent — do not hand-roll lock
logic with plain GET/SET, which is race-prone). Lock key format:
`lock:{job_type}:{workspace_id}`. Default TTL: 2x the job type's
TIMEOUT above (so a crashed holder's lock expires before it could
plausibly still be legitimately running), with lock renewal
("heartbeat extend") every 30 seconds for genuinely long-running
jobs so a slow-but-alive job doesn't lose its lock in the meantime.

Validation

Reject any scheduled job implementation that does not acquire a
distributed lock scoped to `job_type + workspace_id` before
executing.

Reject any consumer implementation that processes an event without
checking `processed_events` first.

---

CACHE

Redis

---

CACHE_KEYS

Workspace

Dashboard

Permissions

Reports

Settings

Feature Flags

Session

---

CACHE_POLICY

TTL Based

Workspace Scoped

Automatic Invalidation

Read Through

Write Through

---

STORAGE

Private Objects

Public Assets

Exports

Backups

Logs

Audit Files

---

SECRET_MANAGEMENT

Encryption Required

Rotation Supported

Environment Scoped

Access Logged

Never Exposed

---

HEALTH_CHECKS

API

Database

Redis

Queue

Storage

Email

Webhook

Scheduler

Background Workers

---

OBSERVABILITY

Metrics

Logs

Traces

Audit Events

Alerts

Dashboards

---

API

GET

/api/v1/platform/health

GET

/api/v1/platform/status

GET

/api/v1/platform/config

GET

/api/v1/platform/features

PATCH

/api/v1/platform/features/{id}

POST

/api/v1/platform/cache/clear

POST

/api/v1/platform/jobs/retry

GET

/api/v1/platform/jobs

GET

/api/v1/platform/metrics

---

DATABASE

feature_flags

platform_configuration

scheduled_jobs

job_history

system_health

cache_metadata

audit_logs

---

EVENTS

SYSTEM_STARTED

SYSTEM_STOPPED

HEALTH_CHANGED

FEATURE_FLAG_UPDATED

JOB_CREATED

JOB_COMPLETED

JOB_FAILED

CACHE_INVALIDATED

CONFIGURATION_UPDATED

SECRET_ROTATED

---

ERRORS

SERVICE_UNAVAILABLE

INVALID_CONFIGURATION

FEATURE_FLAG_NOT_FOUND

CACHE_FAILURE

QUEUE_FAILURE

JOB_TIMEOUT

SECRET_ACCESS_DENIED

HEALTH_CHECK_FAILED

---

MONITORING

API Availability

Database Latency

Queue Depth

Cache Hit Rate

Worker Utilization

Scheduler Success Rate

Background Job Duration

Storage Usage

Error Rate

System Uptime

---

PERFORMANCE

API Availability

99.9%

---

Health Check

P95

<200ms

---

Queue Processing

P95

<1 Second

---

Cache Hit Rate

>95%

---

SECURITY

Workspace Isolation

RBAC Required

HTTPS Only

Audit Required

Encrypted Secrets

Signed Internal Requests

Least Privilege Access

---

BUSINESS_RULES

Platform Services Are Shared Across Modules

Feature Flags Are Environment Scoped

Secrets Never Stored In Plaintext

Background Jobs Are Idempotent

Health Checks Must Not Mutate Data

Platform Failures Must Be Auditable

Every Scheduled Job Is Traceable

---

DEPENDENCIES

Authentication

Workspace

RBAC

Finance Engine

Reconciliation Engine

Reports

Notifications

Billing

Monitoring

---

ACCEPTANCE

✓ Health Monitoring

✓ Feature Flags

✓ Configuration Management

✓ Background Jobs

✓ Queue Management

✓ Scheduler

✓ Cache Management

✓ Secret Management

✓ Storage Management

✓ Audit Generated

---

CURSOR_RULES

Never hardcode configuration values.

Always read configuration from the platform service.

Never expose secrets to the frontend.

Always encrypt stored secrets.

Always isolate cache by workspace_id.

Always process background jobs asynchronously.

All scheduled jobs must be idempotent.

Feature flags must be evaluated server-side.

Every platform action must generate an audit event.

Platform failures must never compromise tenant isolation.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE