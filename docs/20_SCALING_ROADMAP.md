# 20_SCALING_ROADMAP.md

---
document:
  id: DOC-020
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

MOD-SCALING

owner:

PLATFORM

---

goal:

Scale Ganaka from MVP to enterprise without architectural rewrites.

---

SCALING_PRINCIPLES

Keep Architecture Simple

Avoid Premature Optimization

Horizontal Scaling Preferred

Stateless APIs

Background Processing

Idempotent Jobs

Event Driven Where Beneficial

Database First Consistency

Observability First

Security By Default

---

PHASES

PHASE_1

customers

10

architecture

Hybrid Architecture (Core Platform Service — Spring Boot — and AI
Service — FastAPI — per docs/21_HYBRID_ARCHITECTURE.md; both
services exist from Phase 1, not introduced at a later phase)

Next.js

Single PostgreSQL

Single Redis

Single Worker

Single Region

---

PHASE_2

customers

100

additions

Redis Cache

Background Queue

Connection Pool

CDN

Scheduled Workers

---

PHASE_3

customers

1000

additions

Multiple Workers

Dedicated Queue

Read Replica

Horizontal API Scaling

Dedicated Monitoring

---

PHASE_4

customers

10000

additions

Load Balancer

Dedicated Cache Cluster

Dedicated Worker Cluster

Database Read Replicas

Distributed Object Storage

---

PHASE_5

customers

100000

additions

Regional Deployments

Distributed Queue

Autoscaling

Database Partitioning

Disaster Recovery Region

---

SCALABLE_COMPONENTS

Authentication

Authorization

Dashboard

Reconciliation

Reports

Notifications

Billing

Admin

Monitoring

API

---

DATABASE_STRATEGY

Stage_1

Single PostgreSQL

---

Stage_2

Indexes

Query Optimization

Vacuum

Connection Pool

---

Stage_3

Read Replica

---

Stage_4

Partition Large Tables

Audit

Logs

Reconciliation

---

Stage_5

Sharding Only If Required

---

CACHE_STRATEGY

Stage_1

Optional

---

Stage_2

Session Cache

Permission Cache

Dashboard Cache

---

Stage_3

Query Cache

API Cache

Report Cache

---

QUEUE_STRATEGY

Stage_1

Redis

---

Stage_2

Retry Queue

Dead Letter Queue

---

Stage_3

Priority Queue

Parallel Workers

---

BACKGROUND_JOBS

Daily Reconciliation

Order Import

Settlement Import

Report Generation

Notification Delivery

Cleanup

Backup

Monitoring

---

API_STRATEGY

REST

Versioned

Stateless

JWT Authentication

Rate Limited

Idempotent

---

PERFORMANCE_TARGETS

Login

<300ms

---

Dashboard

<500ms

---

Search

<300ms

---

Reconciliation

10000 Orders

<5 Minutes

---

Report Generation

<30 Seconds

---

IMPORT

50000 Orders

<15 Minutes

---

RESOURCE_LIMITS

Workspace

Unlimited Users

---

Shopify Store

1 Per Workspace

---

Razorpay Account

1 Per Workspace

---

Concurrent Jobs

Configurable

---

Worker Timeout

10 Minutes

---

SCALING_TRIGGERS

CPU

>70%

↓

Scale API

---

Memory

>75%

↓

Scale Worker

---

Queue

>1000 Jobs

↓

Add Workers

---

Database Connections

>80%

↓

Increase Pool

---

API Latency

>500ms

↓

Investigate

---

SECURITY_AT_SCALE

MFA

RBAC

Audit

Encrypted Secrets

Signed JWT

Secret Rotation

Rate Limiting

WAF

---

FAILURE_STRATEGY

Retry

↓

Circuit Breaker

↓

Fallback

↓

Alert

↓

Incident

---

OBSERVABILITY

Metrics

Logs

Tracing

Health Checks

Alerts

Dashboards

Audit

---

DEPLOYMENT

Development

↓

Testing

↓

Staging

↓

Production

---

ROLLBACK

Blue Green

Database Migration Rollback

Feature Flags

Deployment Verification

---

FEATURE_FLAG_STRATEGY

Dark Launch

Percentage Rollout

Workspace Rollout

Instant Disable

Audit Required

---

UPGRADE_STRATEGY

Backward Compatible APIs

Versioned Endpoints

Zero Downtime Deployment

Database Migration First

Application Deployment Second

---

DISASTER_STRATEGY

Automated Backups

Restore Verification

Regional Recovery

Encrypted Backups

Audit

---

BUSINESS_SCALING

10 Customers

Founder Support

---

100 Customers

Dedicated Support

---

1000 Customers

Customer Success Team

---

10000 Customers

Dedicated Account Managers

---

100000 Customers

Enterprise Success Team

---

TECHNICAL_DEBT_POLICY

Document Every Shortcut

No Hardcoded Secrets

No Duplicate Business Logic

No Circular Dependencies

Refactor Before Major Release

---

NON_GOALS

Microservices Before Needed

Kubernetes For MVP

Multi Region Before Demand

Database Sharding Before Need

Complex Event Sourcing

---

SUCCESS_METRICS

99.9% Availability

<1% Failed Jobs

<300ms API P95

<5 Minute Daily Reconciliation

Zero Cross Tenant Data Leak

100% Audit Coverage

---

CURSOR_RULES

Always build for horizontal scalability.

Never sacrifice correctness for performance.

Prefer simple architecture first.

Avoid unnecessary abstractions.

Keep services stateless.

Background heavy operations.

Every new module must expose health metrics.

Every new feature must be observable.

Every database migration must be reversible.

Never introduce breaking API changes.

Never duplicate business rules.

---

ROADMAP_COMPLETE

Foundation

Authentication

Workspace

Shopify

Razorpay

Finance Engine

Reconciliation Engine

Dashboard

Reports

Notifications

Billing

Admin

Monitoring

Backup

Support

Compliance

Scaling

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE