# 09_ERROR_CATALOG.md

# Ganaka Error Catalog

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines every standard error used by Ganaka.

All modules must use these errors.

Never invent new error formats.

Never expose internal exceptions.

---

# STANDARD ERROR RESPONSE

Every API error must return

{
  "timestamp": "...",
  "status": 400,
  "code": "AUTH-001",
  "message": "...",
  "path": "...",
  "requestId": "..."
}

Validation

Reject custom error responses.

---

# ERROR CATEGORIES

AUTH

Authentication

AUTHZ

Authorization

VALIDATION

Input Validation

WORKSPACE

Workspace

SHOPIFY

Shopify Integration

RAZORPAY

Razorpay Integration

PAYMENT

Payments

REFUND

Refunds

SETTLEMENT

Settlements

RECONCILIATION

Reconciliation

DATABASE

Database

SYSTEM

Internal System

EXTERNAL

External Services

FILE

File Upload

RATE_LIMIT

Rate Limiting

UNKNOWN

Unexpected Errors

---

# RULE ERR-001

Category

AUTH

Code

AUTH-001

Message

Invalid email or password.

HTTP Status

401 Unauthorized

Retry

Yes

---

# RULE ERR-002

Category

AUTH

Code

AUTH-002

Message

JWT token expired.

HTTP Status

401 Unauthorized

Retry

Refresh Token

---

# RULE ERR-003

Category

AUTH

Code

AUTH-003

Message

Invalid authentication token.

HTTP Status

401 Unauthorized

Retry

Login Required

---

# RULE ERR-004

Category

AUTHZ

Code

AUTHZ-001

Message

Access denied.

HTTP Status

403 Forbidden

Retry

No

---

# RULE ERR-005

Category

WORKSPACE

Code

WORKSPACE-001

Message

Workspace not found.

HTTP Status

404 Not Found

Retry

No

---

# RULE ERR-006

Category

WORKSPACE

Code

WORKSPACE-002

Message

Workspace access denied.

HTTP Status

403 Forbidden

Retry

No

---

# RULE ERR-007

Category

VALIDATION

Code

VALIDATION-001

Message

Validation failed.

HTTP Status

400 Bad Request

Retry

Correct Input

---

# RULE ERR-008

Category

VALIDATION

Code

VALIDATION-002

Message

Invalid UUID format.

HTTP Status

400 Bad Request

Retry

Correct Input

---

# RULE ERR-009

Category

SHOPIFY

Code

SHOPIFY-001

Message

Shopify synchronization failed.

HTTP Status

502 Bad Gateway

Retry

Automatic Retry

---

# RULE ERR-010

Category

RAZORPAY

Code

RAZORPAY-001

Message

Unable to fetch payment records.

HTTP Status

502 Bad Gateway

Retry

Automatic Retry

---

# RULE ERR-011

Category

PAYMENT

Code

PAYMENT-001

Message

Duplicate payment detected.

HTTP Status

409 Conflict

Retry

Manual Review

---

# RULE ERR-012

Category

REFUND

Code

REFUND-001

Message

Refund mismatch detected.

HTTP Status

409 Conflict

Retry

Manual Review

---

# RULE ERR-013

Category

SETTLEMENT

Code

SETTLEMENT-001

Message

Settlement not found.

HTTP Status

404 Not Found

Retry

Yes

---

# RULE ERR-014

Category

RECONCILIATION

Code

RECONCILIATION-001

Message

Reconciliation failed.

HTTP Status

500 Internal Server Error

Retry

Automatic Retry

---

# RULE ERR-015

Category

DATABASE

Code

DATABASE-001

Message

Database operation failed.

HTTP Status

500 Internal Server Error

Retry

Automatic Retry

---

# RULE ERR-016

Category

FILE

Code

FILE-001

Message

Unsupported file type.

HTTP Status

400 Bad Request

Retry

Upload Supported File

---

# RULE ERR-017

Category

RATE_LIMIT

Code

RATE_LIMIT-001

Message

Too many requests.

HTTP Status

429 Too Many Requests

Retry

Retry Later

---

# RULE ERR-018

Category

EXTERNAL

Code

EXTERNAL-001

Message

External service unavailable.

HTTP Status

503 Service Unavailable

Retry

Automatic Retry

---

# RULE ERR-019

Category

SYSTEM

Code

SYSTEM-001

Message

Unexpected internal error.

HTTP Status

500 Internal Server Error

Retry

Automatic Retry

---

# RULE ERR-020

Category

UNKNOWN

Code

UNKNOWN-001

Message

Unexpected error occurred.

HTTP Status

500 Internal Server Error

Retry

Automatic Retry

---

# ERROR HANDLING RULES

RULE EH-001

Never expose stack traces.

---

RULE EH-002

Never expose SQL errors.

---

RULE EH-003

Never expose internal exception names.

---

RULE EH-004

Always log internal exceptions.

---

RULE EH-005

Always return standardized error responses.

---

# ERROR REVIEW CHECKLIST

Before release verify

✓ Standard response format

✓ Correct HTTP status

✓ Error code assigned

✓ Message standardized

✓ Internal details hidden

✓ Exception logged

✓ Retry policy defined

✓ API documentation updated

---

# REFERENCES

API

docs/05_API_SPECIFICATION.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Coding Standards

docs/08_CODING_STANDARDS.md

Implementation

implementation/

---

END OF DOCUMENT