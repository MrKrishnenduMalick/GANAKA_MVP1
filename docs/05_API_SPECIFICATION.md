# 05_API_SPECIFICATION.md

# Ganaka API Specification

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines all API standards for Ganaka.

It specifies how APIs must be designed, implemented, versioned, secured, and documented.

Business logic belongs in Services.

Database rules belong in 04_DATABASE_SPECIFICATION.md.

---

# API STANDARD

Architecture

REST

Format

JSON

Encoding

UTF-8

Version

v1

Transport

HTTPS Only

Authentication

JWT

---

# RULE API-001

Requirement

Every endpoint must begin with

/api/v1/

Allowed

/api/v1/auth/login

/api/v1/workspaces

Forbidden

/login

/v1/login

/api/login

Validation

Reject endpoints without versioning.

---

# RULE API-002

Requirement

Use REST naming conventions.

Allowed

GET /users

GET /users/{id}

POST /users

PUT /users/{id}

DELETE /users/{id}

Forbidden

/getUsers

/createUser

/updateUser

/deleteUser

Validation

Reject RPC-style endpoints.

---

# RULE API-003

Requirement

Resource names must be plural.

Allowed

/users

/workspaces

/orders

/payments

Forbidden

/user

/payment

/order

Validation

Reject singular resource names.

---

# RULE API-004

Requirement

Every request and response must use DTOs.

Forbidden

Returning Entity objects.

Validation

Reject Entity exposure.

---

# RULE API-005

Requirement

Controllers must never contain business logic.

Allowed

Validation

Service calls

Response mapping

Forbidden

Calculations

Database logic

Business rules

Validation

Reject business logic in controllers.

---

# RULE API-006

Requirement

Every endpoint must validate input.

Validation Includes

Required Fields

Length

Format

Range

Enum Values

UUID Format

Validation

Reject invalid payloads.

---

# RULE API-007

Requirement

All successful responses use standard HTTP status codes.

Examples

200 OK

201 Created

202 Accepted

204 No Content

Validation

Reject incorrect status codes.

---

# RULE API-008

Requirement

Errors must follow a single response format.

Structure (must match docs/09_ERROR_CATALOG.md exactly — that
document is the canonical field list, this rule only cross-references
it so the two do not silently drift again)

timestamp

status

code (e.g. "AUTH-001" — see docs/09_ERROR_CATALOG.md for the full
registry; this field was previously and incorrectly named "error"
in this document, causing a contract mismatch)

message

path

requestId

Validation

Reject custom error formats.

Reject any response using a field named "error" instead of "code".

---

# RULE API-009

Requirement

Never expose

Stack traces

SQL errors

Passwords

Secrets

JWTs

Internal IDs

Validation

Reject sensitive responses.

---

# RULE API-010

Requirement

Pagination is mandatory for list endpoints.

Parameters

page

size

sort

Validation

Reject unlimited list endpoints.

---

# RULE API-011

Requirement

Maximum page size

100

Default page size

20

Validation

Reject oversized requests.

---

# RULE API-012

Requirement

Filtering must use query parameters.

Allowed

/users?status=ACTIVE

/orders?date=2026-01-01

Forbidden

POST filtering

Validation

Reject inconsistent filtering.

---

# RULE API-013

Requirement

Sorting must use

sort=field,direction

Example

sort=createdAt,desc

Validation

Reject custom sorting syntax.

---

# RULE API-014

Requirement

Idempotency is mandatory for financial operations.

Applies To

Payments

Refunds

Settlements

Reconciliation

Validation

Reject duplicate financial execution.

---

# RULE API-015

Requirement

Webhook endpoints must verify signatures.

Forbidden

Unsigned webhook processing.

Validation

Reject invalid signatures.

---

# RULE API-016

Requirement

Rate limiting must exist for

Authentication

Public APIs

Webhook endpoints

Validation

Reject unprotected public endpoints.

---

# RULE API-017

Requirement

Every endpoint requires authentication unless explicitly public.

Public Endpoints

Login

Register

Forgot Password

Health Check

Validation

Reject unsecured private endpoints.

---

# RULE API-018

Requirement

Authorization must be role-based.

Validation

Reject permission bypass.

---

# RULE API-019

Requirement

Every endpoint must generate audit logs when modifying business data.

Applies To

Create

Update

Delete

Financial Actions

Validation

Reject unaudited mutations.

---

# RULE API-020

Requirement

Every endpoint must be documented using OpenAPI.

Documentation Includes

Summary

Description

Parameters

Responses

Errors

Examples

Validation

Reject undocumented endpoints.

---

# RULE API-021

Requirement

Every endpoint contract, wherever defined (docs/05, or any
implementation/*.md API section, including modules added after this
document's initial version — e.g. implementation/12_SHIPPING_RECONCILIATION.md,
implementation/13_TAX_RECONCILIATION.md), must explicitly cover all
of the following, not merely the URL and method:

Request (path/query/body parameters, with types)

Response (exact shape, referencing the owning entity's field list)

Errors (which docs/09_ERROR_CATALOG.md codes this endpoint can
return, or its own namespaced codes per that catalog's per-module
convention)

Validation (which fields are required, their constraints)

HTTP Status (per verb, per outcome — 200/201/204/400/401/403/404/409/422)

Pagination (if a list endpoint — which fields, default/max page size,
per RULE API-010)

Sorting (if a list endpoint — allowed sort fields, per RULE API-013)

Filtering (if a list endpoint — allowed filter fields, per RULE API-012)

Authorization (which permission, per implementation/02_WORKSPACE_AND_RBAC.md,
is required — an endpoint with no stated permission requirement is
a specification gap, not an implicit "any authenticated user")

Idempotency (whether it accepts an Idempotency-Key per
docs/06_SECURITY_REQUIREMENTS.md RULE SEC-025 — state explicitly,
do not leave implicit)

Exposure Tier (`public /api/v1/*` or `internal /internal/v1/*`) and
Status (`active`, `deprecated`, or `sunset-date: YYYY-MM-DD`) — per
docs/06_SECURITY_REQUIREMENTS.md RULE SEC-032. An endpoint is not
fully specified without this pair, even if its request/response
shape is otherwise complete, since Cursor and reviewers rely on it
to tell a deliberate internal-only endpoint apart from one that was
simply never finished.

Validation

Reject any endpoint contract missing any of the above facets.

---

# API REVIEW CHECKLIST

Before completing an API verify

✓ REST compliant

✓ Versioned

✓ DTO used

✓ Validation added

✓ Authentication enforced

✓ Authorization enforced (specific permission named, not just
"authenticated")

✓ Pagination supported (list endpoints)

✓ Sorting / Filtering supported (list endpoints)

✓ Idempotency-Key supported (state-changing endpoints per RULE SEC-025)

✓ Error format correct

✓ Audit logging added

✓ OpenAPI documented

✓ Internal-only endpoints (docs/21_HYBRID_ARCHITECTURE.md) are
explicitly marked as such and excluded from public OpenAPI docs

---

# REFERENCES

Architecture

docs/03_ARCHITECTURE.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Business Rules

docs/07_BUSINESS_RULES.md

Implementation

implementation/

---

END OF DOCUMENT