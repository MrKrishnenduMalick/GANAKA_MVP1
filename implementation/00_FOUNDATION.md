# implementation/00_FOUNDATION.md

---
document:
  id: IMP-000
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

FOUNDATION

owner:

PLATFORM

---

goal:

Provide the core platform foundation required by every module.

---

TECH_STACK

Frontend

Next.js 15

React 19

TypeScript

TailwindCSS

shadcn/ui

TanStack Query

---

Backend (Core Platform Service — owns everything except AI reconciliation;
see docs/21_HYBRID_ARCHITECTURE.md OWNERSHIP_MATRIX)

Spring Boot 3

Java 21

Spring Security

Spring Data JPA

Spring Validation

Spring Scheduler

---

AI Service (owns AI Reconciliation, AI Matching, Intelligent
Suggestions, future ML; separate deployable, separate codebase;
see docs/21_HYBRID_ARCHITECTURE.md)

FastAPI

Python 3.12

Pydantic

SQLAlchemy (read path only against shared PostgreSQL)

AsyncIO

---

Database

PostgreSQL

---

Cache

Redis

---

Queue

Redis Streams

---

Storage

Supabase Storage

---

Authentication

JWT

Refresh Token

Email OTP

Google OAuth

---

Build

Gradle

---

Container

Docker

Docker Compose

---

Hosting

Frontend

Vercel

---

Backend

Render

---

Database

Supabase PostgreSQL

---

Storage

Supabase Storage

---

ENVIRONMENTS

LOCAL

DEV

STAGING

PRODUCTION

---

PROJECT_STRUCTURE

frontend

backend (Core Platform Service — Spring Boot)

ai-service (AI Service — FastAPI; separate deployable, own
Dockerfile, own dependency lockfile, never imports backend/ code
or vice versa — communicate only via HTTP per
docs/21_HYBRID_ARCHITECTURE.md)

database

shared

docs

scripts

docker

.github

---

BACKEND_MODULES (Core Platform Service — Spring Boot)

auth

workspace

users

rbac

shopify

razorpay

finance

reconciliation (orchestration only: receives reconciliation
requests, persists results/exceptions, serves reconciliation APIs
to frontend. Does NOT contain matching algorithm logic — that is
delegated to ai-service. See docs/21_HYBRID_ARCHITECTURE.md
OWNERSHIP_MATRIX and implementation/07_RECONCILIATION_ENGINE.md
AI_SERVICE_DELEGATION.)

dashboard

reports

notifications

billing

admin

monitoring

---

AI_SERVICE_MODULES (AI Service — FastAPI; see
docs/21_HYBRID_ARCHITECTURE.md for full spec)

matching_engine (implements the DISCREPANCY DECISION TABLE in
implementation/07_RECONCILIATION_ENGINE.md)

suggestion_engine (manual-review recommendations)

anomaly_detection

model_registry (future ML)

---

FRONTEND_MODULES

landing

auth

dashboard

settings

reports

billing

admin

profile

support

---

CORE_ENTITIES

User

Workspace

Role

Permission

Session

Subscription

Order

Payment

Settlement

Reconciliation

Notification

AuditLog

---

ARCHITECTURE

Client

↓

API

↓

Service

↓

Repository

↓

Database

---

REQUEST_PIPELINE

Request

↓

Validation

↓

Authentication

↓

Authorization

↓

Business Logic

↓

Audit

↓

Response

---

GLOBAL_RULES

Every endpoint authenticated unless public.

Every request validated.

Every mutation audited.

Every business rule inside service layer.

No business logic inside controllers.

No SQL inside controllers.

No secrets in source code.

---

DEPENDENCY_RULES

Controller

↓

Service

↓

Repository

↓

Database

No reverse dependency.

No circular dependency.

---

CONFIGURATION

application.yml

application-dev.yml

application-prod.yml

Environment Variables

Secrets Manager

---

SECURITY

HTTPS Only

JWT Authentication

RBAC

Password Hashing

Rate Limiting

CSRF: not applicable to the bearer-transported access token; the
refresh-token cookie is protected via SameSite=Strict instead of a
CSRF token. See implementation/01_AUTHENTICATION.md TOKEN_TRANSPORT
for the full, authoritative rule — do not restate a shorter/different
version of this rule elsewhere.

Input Validation

Output Encoding

---

ERROR_HANDLING

Global Exception Handler

Standard Error Response

Request ID

Correlation ID

Audit ID

---

LOGGING

Structured JSON

INFO

WARN

ERROR

No Sensitive Data

---

AUDIT

Login

Logout

Create

Update

Delete

Permission Change

Billing Change

Admin Action

---

DATABASE_RULES

UUID Primary Keys

Foreign Keys

Indexes

Soft Delete Where Required

Flyway Migrations

UTC Timestamps

---

API_RULES

REST

Versioned

/api/v1

JSON Only

Pagination

Filtering

Sorting

Idempotent Mutations

---

BACKGROUND_JOBS

Scheduler

Queue

Retry

Dead Letter Queue

Audit

---

OBSERVABILITY

Health

Metrics

Tracing

Logs

Alerts

---

TESTING

Unit

Integration

API

Repository

Security

---

BUILD_PIPELINE

Compile

↓

Test

↓

Static Analysis

↓

Build Docker

↓

Deploy

---

NON_FUNCTIONAL

Stateless

Scalable

Secure

Observable

Maintainable

Testable

---

CURSOR_RULES

Never duplicate business logic.

Never bypass validation.

Never bypass RBAC.

Never bypass audit.

Use constructor injection only.

Follow package structure.

Every feature must include tests.

Every API must be documented.

Every database change must use Flyway.

Every service must expose metrics.

---

DEFINITION_OF_DONE

Project Builds

Tests Pass

No Critical Vulnerabilities

Flyway Successful

Health Endpoint Healthy

Audit Enabled

Monitoring Enabled

Documentation Updated

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE