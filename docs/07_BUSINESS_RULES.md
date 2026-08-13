# 07_BUSINESS_RULES.md

# Ganaka Business Rules

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines all business rules governing Ganaka.

Business rules describe how the system behaves.

They are independent of

- Database
- API
- UI
- Programming Language
- Framework

Every implementation must follow these rules.

---

# BUSINESS DOMAIN

Ganaka automates financial reconciliation.

Primary Business Objects

- Workspace
- User
- Store
- Order
- Payment
- Refund
- Settlement
- Reconciliation
- Report
- Notification

---

# RULE BR-001

Requirement

Every business action belongs to exactly one workspace.

Validation

Reject actions without workspace context.

---

# RULE BR-002

Requirement

A user may belong to multiple workspaces.

A user's permissions are evaluated independently within each workspace.

Validation

Never share permissions across workspaces.

---

# RULE BR-003

Requirement

A workspace owns all business data created within it.

Validation

Prevent cross-workspace ownership.

---

# RULE BR-004

Requirement

Every imported financial record must be uniquely identifiable.

Business Keys

- Order ID
- Payment ID
- Refund ID
- Settlement ID

Validation

Reject duplicate business records.

---

# RULE BR-005

Requirement

A reconciliation compares financial records originating from different systems.

Minimum Sources

- Commerce Platform
- Payment Gateway

Validation

Do not reconcile incomplete datasets.

---

# RULE BR-006

Requirement

Each reconciliation must produce exactly one final status.

Allowed Status

- MATCHED
- PARTIALLY_MATCHED
- UNMATCHED
- ERROR

Validation

Reject multiple final states.

---

# RULE BR-007

Requirement

Completed reconciliations are immutable.

Allowed

View

Export

Audit

Forbidden

Edit

Delete

Recalculate in place

Validation

Create a new reconciliation instead.

---

# RULE BR-008

Requirement

Refunds must be reconciled independently from original payments.

Validation

Do not merge refund reconciliation into payment reconciliation.

---

# RULE BR-009

Requirement

Duplicate payments must be flagged.

Validation

Duplicate payments require manual review.

---

# RULE BR-010

Requirement

Missing settlements must generate reconciliation exceptions.

Validation

Settlement mismatches cannot be silently ignored.

---

# RULE BR-011

Requirement

Negative balances are allowed only when supported by business context.

Validation

Reject invalid negative financial values.

---

# RULE BR-012

Requirement

Every imported transaction must pass validation before reconciliation.

Validation Includes

- Required Fields
- Amount
- Currency
- Date
- Source Identifier

Validation

Reject invalid transactions.

---

# RULE BR-013

Requirement

Reconciliation must be deterministic.

The same input must always produce the same output.

Validation

Reject non-deterministic calculations.

---

# RULE BR-014

Requirement

Business calculations must never modify original imported records.

Validation

Original financial data is read-only.

---

# RULE BR-015

Requirement

Currency conversion is outside current product scope.

Validation

Reject automatic currency conversion.

---

# RULE BR-016

Requirement

Every financial exception requires classification.

Allowed Types

- Missing Payment
- Missing Settlement
- Duplicate Payment
- Amount Mismatch
- Refund Mismatch
- Unknown Error

Validation

Reject uncategorized exceptions.

---

# RULE BR-017

Requirement

Business reports must use reconciled data only.

Validation

Do not generate reports from unverified records.

---

# RULE BR-018

Requirement

Every manual business action must be auditable.

Examples

- Manual Approval
- Manual Override
- Exception Resolution

Validation

Audit entry required.

---

# RULE BR-019

Requirement

Business notifications are generated only for meaningful events.

Examples

- Reconciliation Completed
- Settlement Missing
- Duplicate Payment
- Critical Failure

Validation

Ignore informational noise.

---

# RULE BR-020

Requirement

Business rules are implementation-independent.

They must remain valid regardless of

- Programming Language
- Framework
- Database
- Infrastructure

Validation

Do not encode implementation assumptions into business rules.

---

# BUSINESS REVIEW CHECKLIST

Before implementing business logic verify

✓ Workspace ownership enforced

✓ Financial records validated

✓ Duplicate detection enabled

✓ Settlement verification completed

✓ Reconciliation deterministic

✓ Reports use reconciled data

✓ Audit logging enabled

✓ Notifications generated correctly

✓ Original records preserved

✓ Business rules unchanged

---

# REFERENCES

Product Requirements

docs/02_PRODUCT_REQUIREMENTS.md

Database

docs/04_DATABASE_SPECIFICATION.md

API

docs/05_API_SPECIFICATION.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Implementation

implementation/

---

END OF DOCUMENT