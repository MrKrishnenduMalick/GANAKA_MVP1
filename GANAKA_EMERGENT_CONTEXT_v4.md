# GANAKA – EMERGENT CONTEXT

Version: MVP v1.2

---

## SOURCE OF TRUTH

- The repository is the primary implementation reference.
- This document defines product goals, constraints, and implementation priorities only.
- If repository and document conflict: report the conflict. Do not guess which is correct.

---

## PROJECT

Ganaka is a financial reconciliation SaaS for Shopify-based D2C businesses.

Imports Shopify + Razorpay data, reconciles transactions via deterministic business rules, and presents auditable financial evidence. Goal: eliminate manual reconciliation with accurate, explainable, trustworthy reporting.

**Target:** Production-quality MVP for 10–50 paying customers. Not a hackathon project. Not the final enterprise version.

---

## MVP FEATURES

Implement only:

Authentication · User Profile · Workspace · Shopify Integration · Razorpay Integration · Order/Payment/Refund/Settlement Import · Synchronization Engine · Financial Reconciliation Engine · Dashboard · Reports · Audit Center · Settings

---

## OUT OF SCOPE

AI Features · Billing · Subscriptions · Team Management · Email Campaigns · WhatsApp · Tally · Zoho · ERP Integrations · Advanced Analytics · Kafka · Kubernetes · Microservices

---

## PRODUCT PRINCIPLES

Correctness > Transparency > Auditability > Reliability. Financial correctness outweighs feature quantity.

## PRIORITY ORDER

1. Correctness
2. Security
3. Reliability
4. Maintainability
5. User Experience
6. Performance

Never optimize for scale before correctness.

---

## FINANCIAL RULES

Detect: Ghost Orders · Missing Payments · Duplicate Payments · Amount Mismatch · Refund Mismatch · Settlement Difference · Money At Risk

Every reconciliation result includes: Evidence, Business Rule, Calculation, Explanation, Recommendation.

Never guess financial values. If data is unavailable, state what's missing — do not estimate.

---

## FINANCIAL INTEGRITY

- Imported financial records are immutable — never modify historical financial data.
- Corrections happen only through reconciliation records, never edits to source data.
- Every financial calculation must be deterministic and reproducible.
- Every calculation and correction must remain traceable to its source (auditability).

---

## ENGINEERING RULES

- Continue from existing implementation — never redesign the architecture.
- Never rewrite stable modules without justification.
- Reuse existing services; never duplicate business logic.
- Follow SOLID; keep implementation modular; separate business logic from controllers.
- Prefer maintainability over cleverness.

---

## DATABASE / API / SECURITY

**Database:** preserve schema, use migrations for changes, maintain referential integrity, prevent duplicate imports, never delete financial records.

**API:** preserve existing contracts and backward compatibility, REST, versioned, validate every request, consistent error responses.

**Security:** JWT auth, refresh tokens, password hashing, RBAC, rate limiting, input validation, secure secret storage, audit logging. Never expose secrets.

---

## USER EXPERIENCE

Every page: Loading, Empty, Error, Success states. Must be understandable by non-technical finance users.

---

## AI CONSTRAINTS

Never:

- Invent APIs, database tables, business rules, or financial calculations.
- Break existing architecture or API contracts.
- Duplicate existing business logic.
- Refactor beyond what the milestone requires.
- Add features beyond MVP scope (feature creep).
- Claim implementation, testing, or verification without evidence.

If information is missing: state what's missing explicitly. If context fills: stop, summarize completed/remaining work, list modified files, wait for **CONTINUE**.

---

## MILESTONES

Build incrementally, one at a time, in order:

1. Authentication & Workspace
2. Shopify Integration
3. Razorpay Integration
4. Financial Reconciliation Engine
5. Dashboard, Reports & Audit Center
6. Production Readiness & Beta Release

Never skip or combine milestones.

---

## DEFINITION OF DONE

A milestone is complete only when:

- Planned functionality is implemented.
- Documentation is synchronized (docs, API, DB, `PROJECT_STATUS.md`).
- No placeholder/mock implementations remain.
- No Critical issues remain.
- **Verified:** project builds with no compilation errors.
- **Verified:** database migrations run successfully.
- **Verified:** new/changed API endpoints function correctly.
- **Verified:** core workflow works end-to-end.

---

## IMPLEMENTATION EVIDENCE

Each milestone's `IMPLEMENTATION_REPORT.md` must state:

- Features completed
- Files modified
- Database changes
- API changes
- Documentation updates
- Known limitations
- Remaining work
- Risks introduced (if any)

Also generate: `FILES_CHANGED.md`, `PROJECT_STATUS.md`, `NEXT_MILESTONE.md`.

---

## SUCCESS CRITERIA

A merchant can, without developer help: Register → Login → Connect Shopify → Connect Razorpay → Import Orders/Payments/Refunds/Settlements → Run Reconciliation → View Dashboard → Understand every discrepancy → Download reports.
