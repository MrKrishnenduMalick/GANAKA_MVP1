# 04_DATABASE_SPECIFICATION.md

# Ganaka Database Specification

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document is the single source of truth for the database.

It defines database rules only.

Do not place API, business logic, or security rules here.

---

# DATABASE

Database Engine

PostgreSQL

ORM

Spring Data JPA

Migration Tool

Flyway

Timezone

UTC

Character Set

UTF-8

---

# RULE DB-001

Requirement

Use PostgreSQL for every environment.

Applies To

Development

Testing

Production

Forbidden

MySQL

SQLite

MongoDB

Validation

Reject any implementation using another database.

---

# RULE DB-002

Requirement

Every business table must use UUID as the primary key.

Implementation

```sql
id UUID PRIMARY KEY
```

Forbidden

AUTO_INCREMENT

BIGINT

SERIAL

Validation

Fail review if UUID is missing.

---

# RULE DB-003

Requirement

Every table must contain

- id
- created_at
- updated_at

Validation

Reject tables missing any required column.

---

# RULE DB-004

Requirement

Financial tables must also include

- created_by
- updated_by

Validation

Reject financial tables without audit ownership.

---

# RULE DB-005

Requirement

Use snake_case for

- tables
- columns
- constraints
- indexes

Allowed

payment_transaction

workspace_member

Forbidden

PaymentTransaction

PaymentTable

Validation

Reject non-snake_case names.

---

# RULE DB-006

Requirement

Table names must be singular.

Allowed

workspace

user

payment

Forbidden

users

payments

transactions

Validation

Reject plural table names.

---

# RULE DB-007

Requirement

Every foreign key must be explicitly declared.

Implementation

```sql
workspace_id UUID REFERENCES workspace(id)
```

Forbidden

Implicit relationships

Validation

Reject missing foreign keys.

---

# RULE DB-008

Requirement

Every table belonging to a tenant must include

workspace_id

Validation

Reject tenant tables without workspace isolation.

---

# RULE DB-008a — TENANT ISOLATION STRATEGY (explicit decision;
resolves prior ambiguity between Row Level Security and
Application-Level Isolation — do not leave this to inference)

Decision

APPLICATION-LEVEL ISOLATION. Ganaka does NOT use PostgreSQL Row
Level Security (RLS) as its tenant isolation mechanism.

Mechanism

Every JPA repository in the Core Platform Service extends a shared
base repository/interceptor that mandatorily injects
`WHERE workspace_id = :currentWorkspaceId` into every query,
sourced from the authenticated request's JWT `workspace_id` claim
(never from a request body/query parameter — see
docs/06_SECURITY_REQUIREMENTS.md tenant isolation rules). This is
enforced at the Hibernate/Spring Data layer (e.g. a Hibernate
`@Filter` enabled per-session, or a custom `Specification`/base
repository pattern applied uniformly) so an engineer cannot
accidentally write a query that skips the filter — the filter lives
in shared infrastructure code, not in each individual query.

Why Application-Level Instead Of RLS

- The AI Service (docs/21_HYBRID_ARCHITECTURE.md) connects with its
  own least-privilege DB role and reads tables directly — RLS
  policies would need to be duplicated/maintained for that role too,
  and application-level filtering (a `workspace_id` bind parameter
  the Core Platform Service already computes and passes in the
  internal API call) is simpler to keep in sync with the one
  OWNERSHIP_MATRIX than maintaining Postgres-side policies for two
  separate application identities.
- The team's primary expertise (Spring Data JPA) is Java-side; a
  bug in a shared repository base class is easier to catch in code
  review and unit tests (RULE TEST-018 requires ≥90% business logic
  coverage) than a Postgres RLS policy bug, which surfaces silently
  as a query returning zero/extra rows with no application-level
  error to test against.

Defense In Depth (optional, recommended for Production Readiness,
not required for V1)

Postgres RLS MAY be added later as a second, redundant layer (belt
and suspenders) once the application-level filter has proven
correct in production — if added, it must never become the ONLY
isolation mechanism relied upon; application-level filtering remains
mandatory regardless.

Validation

Reject any repository/query that does not go through the shared
workspace-scoped base repository.

Reject any claim that RLS alone provides tenant isolation without
the application-level filter also being present.

---

# RULE DB-009

Requirement

Delete operations must use soft delete.

Implementation

deleted_at TIMESTAMP NULL

Forbidden

DELETE FROM

unless explicitly approved.

Validation

Reject permanent deletion.

---

# RULE DB-010

Requirement

Every timestamp must use UTC.

Forbidden

Local timezone storage.

Validation

Reject timezone-dependent timestamps.

---

# RULE DB-011

Requirement

Money must use DECIMAL.

Implementation

DECIMAL(18,2)

Forbidden

FLOAT

DOUBLE

Validation

Reject floating-point money.

---

# RULE DB-012

Requirement

Amounts cannot be negative unless business rules explicitly allow them.

Validation

Reject invalid monetary values.

---

# RULE DB-013

Requirement

Every reconciliation record must be immutable after completion.

Forbidden

UPDATE completed reconciliation

Validation

Reject mutable financial history.

---

# RULE DB-014

Requirement

Indexes must exist on

- workspace_id
- created_at
- status
- foreign keys

Validation

Reject large tables without indexes.

---

# RULE DB-015

Requirement

Unique constraints must enforce business uniqueness.

Examples

email

shopify_store_id

razorpay_account_id

Validation

Reject duplicate business identifiers.

---

# RULE DB-016

Requirement

Flyway controls every schema change, with no exceptions — this
includes the `ai_`-prefixed tables the AI Service owns at the DML
level (docs/21_HYBRID_ARCHITECTURE.md DATA_OWNERSHIP). The AI Service
has its own read/write DB role for row-level operations on those
tables, but DDL (CREATE/ALTER/DROP TABLE) for every table in the
shared PostgreSQL instance lives in one Flyway migration history
owned by the Core Platform Service repository. The AI Service does
not run a second, independent migration tool (e.g. Alembic) against
the same database — two migration histories against one schema is
how tables silently drift out of sync with their own migration
record.

Forbidden

Manual production schema changes.

A second migration tool (e.g. Alembic) managing DDL for any table,
including `ai_`-prefixed ones.

Validation

Reject schema updates outside Flyway.

Reject any AI Service dependency on an independent schema-migration
tool.

---

# RULE DB-017

Requirement

Migration files are immutable.

Forbidden

Editing executed migrations.

Validation

Create a new migration instead.

---

# RULE DB-018

Requirement

Never remove production columns.

Allowed

Deprecation

Migration

Replacement

Validation

Reject destructive schema changes.

---

# RULE DB-019

Requirement

Every financial action must be auditable.

Audit Fields

- actor
- timestamp
- action
- entity
- entity_id

Validation

Reject unauditable financial operations.

---

# RULE DB-020

Requirement

Every table must have a clear business owner.

Examples

workspace → Workspace Module

payment → Razorpay Module

order → Shopify Module

reconciliation → Finance Module

Validation

Reject orphan tables.

---

# RULE DB-021

Requirement

Table names are plural snake_case (`shopify_orders`, not
`shopify_order`; `razorpay_payments`, not `razorpay_payment`). The
authoritative name for any table is the one listed in its owning
module's DATABASE section (implementation/*.md). Every other
reference to that table anywhere in the repository — FK annotations
in field lists (`(FK → razorpay_payments)`), DATA_OWNERSHIP grant
lists (docs/21_HYBRID_ARCHITECTURE.md), migration file names — must
cite that exact name, not a singular or otherwise reworded variant.
This document does not restate the full table list; it only sets
the naming rule, to avoid the same list drifting apart in two
places the way RULE SEC-006 already prevents for role names.

Forbidden

A singular or otherwise inconsistent variant of a table name used
anywhere outside its owning module's DATABASE section.

Validation

Reject any FK annotation, ownership grant, or cross-document
reference whose table name does not exactly match the name in that
table's owning module's DATABASE section.

---

# DATABASE REVIEW CHECKLIST

Before completing any database change verify

✓ UUID used

✓ UTC timestamps

✓ Audit fields present

✓ Foreign keys defined

✓ Soft delete supported

✓ Indexes created

✓ Constraints added

✓ Workspace isolation enforced

✓ Flyway migration included

✓ No destructive changes

---

# REFERENCES

Architecture

docs/03_ARCHITECTURE.md

Business Rules

docs/07_BUSINESS_RULES.md

Implementation

implementation/

---

END OF DOCUMENT