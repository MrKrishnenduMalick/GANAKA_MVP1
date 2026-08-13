# 17_BACKUP_AND_DISASTER_RECOVERY.md

---
document:
  id: DOC-017
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

MOD-BACKUP

owner:

PLATFORM

---

goal:

Protect all customer data.

Guarantee recovery.

Prevent data loss.

---

PROTECTED_RESOURCES

DATABASE

OBJECT_STORAGE

USER_UPLOADS

SHOPIFY_TOKENS

RAZORPAY_TOKENS

APPLICATION_CONFIG

FEATURE_FLAGS

AUDIT_LOGS

SUBSCRIPTIONS

RECON_RESULTS

REPORTS

---

BACKUP_POLICY

DATABASE

FULL

daily

---

INCREMENTAL

hourly

---

OBJECT_STORAGE

daily

---

CONFIGURATION

on_change

---

AUDIT

daily

---

ENCRYPTION

AES256

---

COMPRESSION

enabled

---

CHECKSUM

SHA256

---

RETENTION

hourly

48h

---

daily

30d

---

weekly

12w

---

monthly

12m

---

yearly

7y

---

# POINT_IN_TIME_RECOVERY (PITR)

Mechanism

PostgreSQL continuous WAL (Write-Ahead Log) archiving, in addition
to the periodic full snapshots above (Supabase Postgres provides
this natively — see Supabase's own PITR feature; enable it rather
than building custom WAL shipping).

Granularity

Any point within the last 7 days can be restored to, at
approximately 1-minute granularity (matches the DATABASE RPO of 15
minutes stated in RECOVERY_OBJECTIVES below as an upper bound —
PITR normally does considerably better than that RPO, which is
sized for the worst case where WAL archiving itself has a brief gap).

Use Case

PITR is the mechanism used for RULE-driven scenarios like
"restore to 10 minutes before a bad migration ran" — distinct from
DISASTER_LEVELS restores below, which restore to the latest good
periodic snapshot, not an arbitrary timestamp.

Validation

Reject any disaster-recovery implementation that relies solely on
periodic snapshots without WAL-based PITR for the database tier.

---

# BACKUP_VALIDATION (proactive — distinct from RESTORE_VALIDATION
below, which validates a restore AFTER a real incident; this
validates that backups are trustworthy BEFORE one)

Automated Restore Drill

Weekly, automated: restore the most recent daily snapshot into an
isolated, non-production environment, run the same
RESTORE_VALIDATION checks defined below against it (checksum, FK,
workspace, token, storage, health), then tear the environment down.

Failure Handling

A failed drill fires a CRITICAL alert
(docs/16_MONITORING_AND_OBSERVABILITY.md) immediately — a backup
that can't be proven restorable is treated as equivalent to having
no backup at all, not a lower-priority issue to investigate later.

Validation

Reject any backup strategy without a scheduled, automated restore
drill — a backup that has never been test-restored is unverified by
definition.

---

# REDIS_RECOVERY

Persistence

Redis is configured with AOF (Append Only File) persistence,
`appendfsync everysec` (durability of at most ~1 second of writes
on a hard crash, in exchange for acceptable write throughput —
matches Redis's own documented tradeoff guidance).

What Is Recoverable

Cache entries (docs/11_ENVIRONMENT_SPEC.md / implementation/11_PLATFORM.md
CACHE_KEYS): NOT considered disaster-critical — cache is rebuilt
from PostgreSQL (source of truth) on next read, per CACHE_POLICY
"Read Through". A full Redis cache loss requires no special
recovery process beyond restarting Redis; the application must
tolerate a fully cold cache without error (never assume a cache key
exists).

Queue/Stream entries (implementation/11_PLATFORM.md QUEUE_TYPES):
IS disaster-relevant — an in-flight job lost with Redis is a real
gap (e.g. a queued reconciliation run). AOF persistence
(above) minimizes this to at most ~1 second of recently-enqueued
jobs. On Redis restart/recovery, the reconciliation and import
schedulers additionally run a RECONCILIATION SWEEP — a scheduled job
that checks for any workspace whose expected periodic sync/reconciliation
did not complete in the expected window and re-enqueues it — this
is the actual safety net for queue data loss, not AOF durability
alone, since AOF only bounds the loss window to ~1 second but does
not guarantee zero loss.

Recovery Process

1. Provision new Redis instance (or restart existing).
2. Load most recent AOF file.
3. Application reconnects (standard reconnect/retry logic, no
   manual intervention required for cache; queue workers resume
   consuming from the last acknowledged stream offset).
4. Reconciliation Sweep (above) runs on next scheduled interval to
   catch anything genuinely lost in the ~1 second AOF window.

Validation

Reject any Redis deployment without AOF persistence enabled.

Reject any queue-dependent module (reconciliation, import, billing)
that has no periodic sweep/catch-up job independent of queue
delivery guarantees.

---

BACKUP_STATES

SCHEDULED

↓

RUNNING

↓

VERIFYING

↓

COMPLETED

↓

ARCHIVED

---

FAILED

↓

RETRYING

↓

FAILED

---

BACKUP_WORKFLOW

trigger

scheduler

↓

lock_backup

↓

snapshot_database

↓

backup_storage

↓

backup_configuration

↓

encrypt

↓

compress

↓

checksum

↓

verify

↓

store_metadata

↓

audit

---

RESTORE_WORKFLOW

restore_request

↓

permission_validation

↓

identify_backup

↓

verify_checksum

↓

decrypt

↓

restore_database

↓

restore_storage

↓

restore_configuration

↓

health_check

↓

audit

↓

complete

---

RECOVERY_OBJECTIVES

DATABASE

RPO

15 min

RTO

30 min

---

OBJECT_STORAGE

RPO

1 hour

RTO

1 hour

---

CONFIGURATION

RPO

5 min

RTO

10 min

---

DISASTER_LEVELS

L1

single_service_failure

---

L2

database_failure

---

L3

storage_failure

---

L4

region_failure

---

L5

complete_platform_failure

---

FAILOVER_POLICY

API

automatic

---

DATABASE

manual_approval

---

OBJECT_STORAGE

automatic

---

DNS

manual

---

RESTORE_VALIDATION

database_integrity

checksum_validation

foreign_key_validation

workspace_validation

token_validation

storage_validation

health_validation

---

FAILURE_ACTIONS

backup_failed

↓

retry

↓

alert

↓

incident

---

restore_failed

↓

rollback

↓

alert

↓

incident

---

SECURITY

encrypted_backup

immutable_backup

offsite_backup

checksum_required

signed_metadata

audit_required

rbac_required

---

BACKUP_METADATA

backup_id

type

resource

size

checksum

encrypted

created_at

completed_at

expires_at

status

operator

---

API

POST

/admin/backup/start

GET

/admin/backup/status

GET

/admin/backup/history

POST

/admin/restore

GET

/admin/restore/status

---

EVENTS

BACKUP_STARTED

BACKUP_COMPLETED

BACKUP_FAILED

RESTORE_STARTED

RESTORE_COMPLETED

RESTORE_FAILED

DISASTER_DECLARED

FAILOVER_STARTED

FAILOVER_COMPLETED

---

ALERTS

backup_failure

backup_corrupted

restore_failure

storage_unavailable

database_unavailable

checksum_failed

retention_expired

---

METRICS

backup_duration

backup_size

backup_success

backup_failure

restore_duration

restore_success

restore_failure

storage_growth

recovery_time

---

ACCEPTANCE

✓ Hourly backup succeeds

✓ Daily backup succeeds

✓ Restore verified

✓ Checksums valid

✓ Encryption verified

✓ Retention enforced

✓ Disaster recovery tested

✓ Audit generated

---

CURSOR_RULES

Never restore without verification.

Never overwrite production without approval.

Never skip checksum validation.

Never skip encryption.

Every backup creates an audit record.

Every restore creates an audit record.

Every failure creates an incident.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE