# 00_AI_CONSTITUTION.md

# Ganaka AI Constitution

Version: 1.0.0

Status: Immutable

---

# PURPOSE

This document defines the immutable principles of Ganaka.

These principles cannot be violated.

Every architecture decision, implementation, database change, API, frontend feature, infrastructure component, and deployment must comply with this constitution.

If any implementation conflicts with this document, the implementation is invalid.

---

# ARTICLE 1 — ARCHITECTURE IS IMMUTABLE

The approved architecture is frozen.

Allowed

- Feature implementation
- Bug fixes
- Performance improvements
- Refactoring without changing architecture

Forbidden

- New architecture
- Layer changes
- Module restructuring
- Technology replacement
- Folder restructuring

---

# ARTICLE 2 — SINGLE SOURCE OF TRUTH

Every responsibility has exactly one owner.

Examples

Architecture

→ 03_ARCHITECTURE.md

Database

→ 04_DATABASE_SPECIFICATION.md

API

→ 05_API_SPECIFICATION.md

Security

→ 06_SECURITY_REQUIREMENTS.md

Business Rules

→ 07_BUSINESS_RULES.md

Implementation

→ implementation/

Never duplicate information across documents.

---

# ARTICLE 3 — FINANCIAL CORRECTNESS

Financial accuracy is the highest business priority.

Never

- Lose transactions
- Duplicate transactions
- Modify historical records
- Produce inconsistent balances

Correctness is always more important than performance.

---

# ARTICLE 4 — SECURITY FIRST

Security is mandatory.

Every implementation must enforce

- Authentication
- Authorization
- Workspace Isolation
- Input Validation
- Audit Logging

Security cannot be disabled for convenience.

---

# ARTICLE 5 — MULTI-TENANCY

Every customer is isolated.

A tenant must never access another tenant's data.

Workspace isolation is mandatory throughout the system.

---

# ARTICLE 6 — PRODUCTION READY ONLY

Generate only production-ready code.

Never generate

- Demo code
- Placeholder code
- Mock implementations
- Fake business logic

---

# ARTICLE 7 — BACKWARD COMPATIBILITY

Never introduce breaking changes without explicit approval.

Existing APIs, database contracts, and business logic must remain compatible.

---

# ARTICLE 8 — MODULARITY

Every module owns its own responsibility.

Modules communicate only through defined interfaces.

Never create hidden dependencies.

---

# ARTICLE 9 — TESTABILITY

Every feature must be testable.

Every business rule must be verifiable.

Every critical workflow must have automated tests.

---

# ARTICLE 10 — DOCUMENTATION

Documentation is part of the implementation.

A feature is incomplete if the relevant documentation is outdated.

---

# ARTICLE 11 — NO GUESSING

AI must never invent

- Business rules
- API behavior
- Database structure
- Security policies
- User requirements

If documentation is missing,

STOP

Request clarification.

---

# ARTICLE 12 — CONSISTENCY

Use the same

- Naming
- Error handling
- API style
- Coding conventions
- Logging
- Validation

throughout the repository.

---

# ARTICLE 13 — AUDITABILITY

Every important business action must be traceable.

Critical financial operations must always produce audit records.

---

# ARTICLE 14 — SCALABILITY

Implementations must support future growth without requiring architectural redesign.

Scalability must never compromise correctness.

---

# ARTICLE 15 — QUALITY

Every generated implementation must satisfy

✓ Architecture

✓ Security

✓ Testing

✓ Documentation

✓ Maintainability

✓ Performance

✓ Reliability

Only then is the implementation considered complete.

---

# ARTICLE 16 — AI DETERMINISM

Every API, every database table, every queue, every event, every
DTO, every JSON response, every error, every enum, and every status
value defined anywhere in this repository must be deterministic —
the same named entity must resolve to exactly one shape, one set of
allowed values, and one behavior, regardless of which document
Cursor or Claude Opus is reading at the time.

Concretely, this means:

- An enum's allowed values are defined in exactly one document; every
  other document referencing that enum must cross-reference it, never
  restate a possibly-different subset (this is Article 2 applied
  specifically to enums, called out because enum drift — e.g. the
  role-name drift and MATCH_STATUS gaps found and fixed in this
  repository's review history — is the single most common source of
  AI-generated inconsistency).
- A JSON response shape for a given endpoint is defined once, in the
  API contract for that endpoint (docs/05_API_SPECIFICATION.md /
  the owning implementation/*.md file), never re-derived or
  approximated elsewhere.
- Where a business threshold (tolerance, window, retry count, limit)
  is configurable, its default, minimum, and maximum are stated
  explicitly, in one place, the first time it is introduced — never
  left as the word "configurable" alone.
- Where this repository does not yet specify a concrete value,
  format, or algorithm for something Cursor/Claude Opus needs to
  generate code for, that is a gap in this repository, not license
  for the AI to invent one silently. Per ARTICLE 11, stop and flag
  it rather than guessing — but where practical, this repository's
  authors should close such gaps here, in the specification, rather
  than relying on ARTICLE 11 alone at generation time.

Validation

Reject any implementation where the same named enum, DTO, or status
value has two different definitions traceable to two different
source documents.

---

# ARTICLE 17 — HYBRID ARCHITECTURE INTEGRITY

Ganaka's backend is intentionally split across two services (Core
Platform Service in Java/Spring Boot, AI Service in Python/FastAPI —
full specification in docs/21_HYBRID_ARCHITECTURE.md). This is a
permanent architectural decision, not a transitional state and not
an error to be "fixed" by collapsing to one language.

Any document, comment, generated code file, or prior AI-generated
summary that implies a single-backend system is factually wrong and
must be corrected to match docs/21_HYBRID_ARCHITECTURE.md — never
the other way around. Conversely, any new capability must be placed
in the correct service per that document's OWNERSHIP_MATRIX; "just
add it to whichever service's code I'm already looking at" is a
violation of this article.

Validation

Reject any generated code that implements Core Platform
responsibilities (auth, RBAC, billing, integrations) inside the AI
Service, or AI Reconciliation matching logic inside the Core
Platform Service.

Reject any documentation change that "simplifies" the stack to a
single language without an explicit, reasoned architecture decision
recorded in docs/21_HYBRID_ARCHITECTURE.md first.

---

END OF CONSTITUTION