# AGENTS.md

## Purpose

This repository is designed for autonomous AI software engineering.

All AI agents must follow these instructions.

---

## Source of Truth

Never invent architecture.

Always use:

docs/

implementation/

as the only source of truth.

---

## Development Order

0 Hybrid Architecture (docs/21 — read before Foundation; establishes
which service owns what before any module is built)

1 Foundation

2 Authentication

3 Workspace

4 User Management

5 Shopify

6 Razorpay

7 Finance Engine

8 Reconciliation Engine (Core Platform orchestration) + AI Service
matching engine (parallel track, per docs/21_HYBRID_ARCHITECTURE.md)

9 Dashboard

10 Reports

11 Notifications

12 Platform

13 Shipping Reconciliation

14 Tax Reconciliation

---

## Rules

Never duplicate business logic.

Never create undocumented APIs.

Never modify architecture without updating specifications.

Never create database tables outside specifications.

Never bypass RBAC.

Never bypass audit logging.

Never bypass workspace isolation.

Never expose secrets.

Never store plaintext credentials.

Never generate code that contradicts specifications.

---

## AI Coding Rules (prevents the six failure modes most likely
when Cursor/Claude Opus generates from a large spec repository —
each maps to a concrete check, not just a slogan)

### Prevent Hallucination

Never invent a business threshold, tolerance, retry count, enum
value, or field that is not written in docs/ or implementation/.
If it's missing, stop and flag it (ARTICLE 11) — do not pick a
"reasonable-sounding" number and proceed. Every numeric constant
in generated code must be traceable to a specific RULE/field
definition in this repository, ideally via a code comment citing it
(e.g. `// implementation/07_RECONCILIATION_ENGINE.md TOLERANCE_RULES`).

### Prevent Framework Mixing

Never write Core Platform Service code in anything but Java/Spring
Boot. Never write AI Service code in anything but Python/FastAPI.
Never import one service's code into the other's build. See
docs/21_HYBRID_ARCHITECTURE.md and ARTICLE 17 — the hybrid split is
a fixed boundary, not a style choice per file.

### Prevent Duplicate Code

Before writing a new utility, validator, mapper, or business-rule
check, search the existing codebase for an equivalent first. A
second implementation of the same rule (e.g. two different
password-validation functions) is a defect even if both are
individually correct, because they can silently drift apart later
— exactly the class of bug this repository's own review history
found repeatedly at the specification level (role names, password
length, CSRF stance) before this document existed. Shared logic
belongs in one shared module per service, referenced everywhere
else.

### Prevent Circular Dependencies

Follow the Development Order above strictly — a later module may
depend on an earlier one, never the reverse (e.g. Reconciliation
Engine may depend on Finance Engine, Finance Engine must never
depend on Reconciliation Engine). Within the Core Platform Service,
no two modules may import each other's internals; cross-module
calls go through a defined service interface only.

### Prevent Business Rule Changes

Never alter a documented business rule (any RULE BR-xxx, RULE
SEC-xxx, RULE DB-xxx, tolerance value, retry count, or discrepancy
definition) while implementing it — implementing IS transcribing the
rule into code, not an opportunity to "improve" or "simplify" it. If
a rule appears wrong or produces a bad outcome during implementation,
stop and raise it as a specification question — do not silently
code a different rule and let the specification and the code drift
apart.

### Prevent Schema Drift

Never add, rename, or remove a database column/table without a
corresponding update to the owning implementation/*.md file's field
list, in the same change. Generated migration files and the
specification's field lists must always match — if a migration
exists that isn't reflected in a field list (or vice versa), that
is a defect to fix immediately, not a future cleanup task.

---

## Priority

When conflicts exist

Priority

0

docs/00_AI_CONSTITUTION.md and docs/21_HYBRID_ARCHITECTURE.md
(governing documents — these two are never overridden by anything
below, including implementation/)

↓

1

implementation/

↓

2

docs/ (all other docs/*.md files)

↓

3

Existing Code

↓

4

CLAUDE.md and README.md (onboarding/orientation documents only —
if either ever appears to contradict anything above, that is a bug
in CLAUDE.md/README.md to be fixed, never a signal to change the
governing spec. This tier was previously undefined, which is how a
stack contradiction between CLAUDE.md and the rest of the repository
went unresolved before this document was updated.)

↓

5

AI Assumptions (last resort only — per ARTICLE 11, prefer stopping
and asking over reaching this tier at all)

---

## Code Generation

Generate

Production-ready code only.

No placeholders.

No TODOs.

No fake implementations.

No mock business logic.

---

## Architecture

Respect

Clean Architecture

Repository Pattern

Service Layer

Dependency Injection

Background Jobs

Event Driven Design

---

## Security

Everything authenticated.

Everything authorized.

Everything audited.

Everything validated.

Everything logged.

---

## Testing

Every feature requires

Unit Tests

Integration Tests

API Tests

---

## Output

Generate complete implementations.

Never partial implementations.