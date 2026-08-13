# 10_TESTING_STRATEGY.md

# Ganaka Testing Strategy

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines the testing strategy for Ganaka.

Every feature, bug fix, refactor, and release must comply with this strategy.

Testing is mandatory.

---

# TEST PYRAMID

Level 1

Unit Tests

Level 2

Integration Tests

Level 3

API Tests

Level 4

End-to-End Tests

Priority

Unit > Integration > API > E2E

---

# RULE TEST-001

Requirement

Every business feature must have automated tests.

Validation

Reject untested features.

---

# RULE TEST-002

Requirement

Business logic must be tested using Unit Tests.

Applies To

- Services
- Validators
- Business Rules
- Utility Classes

Forbidden

Testing business logic through Controllers only.

Validation

Reject missing unit tests.

---

# RULE TEST-003

Requirement

Controllers must have Integration Tests.

Verify

- Routing
- Authentication
- Authorization
- Validation
- Response Codes

Validation

Reject untested controllers.

---

# RULE TEST-004

Requirement

Repositories must be tested against PostgreSQL.

Forbidden

Testing SQL using mocked repositories only.

Validation

Reject unverified database queries.

---

# RULE TEST-005

Requirement

Every public API endpoint must have API Tests.

Verify

- Success Responses
- Error Responses
- Validation Errors
- Authorization
- Pagination
- Filtering

Validation

Reject undocumented API behavior.

---

# RULE TEST-006

Requirement

Authentication flows must be fully tested.

Verify

- Login
- Logout
- Token Refresh
- Password Reset
- Unauthorized Access

Validation

Reject incomplete authentication coverage.

---

# RULE TEST-007

Requirement

RBAC must be tested.

Verify

- Owner
- Admin
- Finance Manager
- Analyst
- Viewer

Validation

Reject missing permission tests.

---

# RULE TEST-008

Requirement

Workspace isolation must be tested.

Verify

Tenant A cannot access Tenant B data.

Validation

Reject tenant leakage.

---

# RULE TEST-009

Requirement

Every validation rule must have tests.

Verify

- Required Fields
- Invalid UUID
- Invalid Email
- Invalid Amount
- Invalid Date

Validation

Reject untested validation.

---

# RULE TEST-010

Requirement

Financial calculations must be deterministic.

Validation

Same input must always produce same output.

---

# RULE TEST-011

Requirement

Every reconciliation scenario must be tested.

Minimum Cases

- Perfect Match
- Missing Payment
- Missing Settlement
- Duplicate Payment
- Refund Mismatch
- Partial Match
- Ghost Order (implementation/07_RECONCILIATION_ENGINE.md
  DISCREPANCY DECISION TABLE Step 1)
- COD / Non-Razorpay Gateway Order → NOT_APPLICABLE, correctly
  excluded from Match Accuracy denominator (Step 0 — this is the
  single most business-critical test case in this list; a
  regression here silently reintroduces false-positive Ghost
  Orders for every COD-heavy merchant)
- Settlement Split Across Two Batches (docs/22_FINANCIAL_EDGE_CASES.md
  RULE BR-028)
- Gift Card Partial Payment (docs/22_FINANCIAL_EDGE_CASES.md RULE BR-034)
- Store Credit Refund → excluded from Razorpay refund matching
  (docs/22_FINANCIAL_EDGE_CASES.md RULE BR-035)

Validation

Reject incomplete reconciliation testing.

---

# RULE TEST-012

Requirement

External integrations must be mocked during Unit Tests.

Applies To

- Shopify
- Razorpay
- Email
- Notifications

Validation

Reject external API dependency in unit tests.

---

# RULE TEST-013

Requirement

Critical production bugs require Regression Tests.

Validation

Reject bug fixes without regression coverage.

---

# RULE TEST-014

Requirement

Generated reports must be verified.

Verify

- CSV
- PDF
- Summary Data
- Totals

Validation

Reject incorrect report generation.

---

# RULE TEST-015

Requirement

Audit logging must be tested.

Verify

- User
- Workspace
- Timestamp
- Action
- Entity

Validation

Reject missing audit verification.

---

# RULE TEST-016

Requirement

Error responses must be tested.

Verify

- HTTP Status
- Error Code
- Message
- Response Structure

Validation

Reject inconsistent errors.

---

# RULE TEST-017

Requirement

Performance-sensitive operations require performance tests.

Examples

- Reconciliation Engine
- Large Imports
- Report Generation

Validation

Reject performance regressions.

---

# RULE TEST-018

Requirement

Minimum automated test coverage.

Business Logic

≥ 90%

Controllers

≥ 80%

Repositories

≥ 80%

Overall

≥ 85%

Validation

Reject builds below threshold.

---

# RULE TEST-019

Requirement

CI must execute all automated tests.

Validation

Reject deployments with failing tests.

---

# RULE TEST-020

Requirement

No production release without passing test suite.

Required

✓ Unit Tests

✓ Integration Tests

✓ API Tests

✓ Regression Tests

✓ Security Tests

Validation

Block release if any required suite fails.

---

# RULE TEST-021

Requirement

Webhook Testing (Shopify + Razorpay)

Coverage Required

- Valid signature accepted
- Invalid/tampered signature rejected (RULE SEC-021)
- Missing signature header rejected
- Replayed event_id rejected without reprocessing (RULE SEC-022)
- Stale timestamp rejected (RULE SEC-023, Razorpay only)
- Out-of-order delivery handled correctly (e.g. `orders/paid`
  arriving before `orders/create` due to redelivery — must not
  crash, must reconcile once both are eventually processed)
- Malformed/truncated payload handled without crashing the worker
- Duplicate delivery of an already-processed event is a no-op

Validation

Reject any webhook handler shipped without tests for both the
valid-signature and invalid-signature paths, at minimum.

---

# RULE TEST-022

Requirement

Performance Testing

Coverage Required

Every module's stated PERFORMANCE targets (e.g.
implementation/07_RECONCILIATION_ENGINE.md <10 min per 100,000
transactions; implementation/12_SHIPPING_RECONCILIATION.md <2 min
per 10,000 line items) must have an automated performance test that
fails CI if the target regresses beyond 20% of the stated value.
Run against production-sized synthetic datasets, not toy fixtures —
a performance test against 100 rows validates nothing about a
100,000-row target.

Validation

Reject any module with a stated PERFORMANCE target but no
corresponding performance test.

---

# RULE TEST-023

Requirement

Security Testing

Coverage Required

- Automated dependency vulnerability scanning (every build — e.g.
  `gradle dependencyCheck` / `pip-audit`, fail build on Critical/High
  findings)
- Automated SAST (static analysis for injection, hardcoded secrets,
  insecure deserialization) on every pull request
- Tenant isolation test suite: for every list/detail endpoint,
  assert that Workspace A's authenticated user cannot retrieve
  Workspace B's data by ID substitution (IDOR regression suite —
  this is the single most valuable security test category for a
  multi-tenant financial product and must exist for every resource
  type, not spot-checked on a few)
- Annual third-party penetration test (external, not self-assessed)
  before each major version's production readiness sign-off
  (docs/12_RELEASE_PROCESS.md)

Validation

Reject any new resource type/endpoint added without a corresponding
cross-tenant-access-denied test.

---

# RULE TEST-024

Requirement

AI Service Testing (docs/21_HYBRID_ARCHITECTURE.md)

Coverage Required

- Contract tests between Core Platform Service and AI Service,
  validated against the shared request/response schema in
  docs/21_HYBRID_ARCHITECTURE.md COMMUNICATION, run in both
  services' CI pipelines against the same schema version
- Determinism test: given a fixed `model_version` and fixed input,
  the AI Service's matching output must be byte-identical across
  repeated runs (ties to implementation/07_RECONCILIATION_ENGINE.md
  BUSINESS_RULES "reconciliation must be deterministic" and ARTICLE
  16 AI DETERMINISM — non-determinism under a stable model_version
  is a test failure, not acceptable variance)
- Full DISCREPANCY DECISION TABLE coverage: one test case per
  Step (0 through 5) and per MATCH_STATUS value, including the
  NOT_APPLICABLE/COD path (this closes the same gap flagged in
  RULE TEST-011's reconciliation test list — that list must be
  updated to explicitly include a COD/NOT_APPLICABLE test case,
  which was previously missing there)
- Degraded-mode test: Core Platform Service continues serving
  Dashboard/Reports correctly when the AI Service is simulated as
  fully unavailable (circuit breaker open)

Validation

Reject any AI Service release without a passing determinism test
against its declared model_version.

---

# RULE TEST-025

Requirement

Load Testing

Coverage Required

- Simulate peak concurrent usage (define peak as the largest
  connected workspace's expected traffic × 10, as a baseline
  starting assumption until real production data refines it)
  against API, webhook ingestion, and reconciliation job submission
  endpoints
- Verify autoscaling / worker concurrency settings
  (implementation/11_PLATFORM.md BACKGROUND_JOBS CONCURRENCY) hold
  up under load without cross-workspace queuing starvation (one
  workspace's large sync must not delay another workspace's jobs
  indefinitely — verify via the per-workspace distributed lock
  design, not a global queue lock)
- Run before every major version's production readiness sign-off,
  not only once at initial launch

Validation

Reject production readiness sign-off without a load test report for
the current release.

---

# TEST REVIEW CHECKLIST

Before approving code verify

✓ Unit Tests Added

✓ Integration Tests Added

✓ API Tests Added

✓ Webhook Tests Added (if touching a webhook handler)

✓ Validation Tested

✓ RBAC Tested

✓ Workspace Isolation Tested (cross-tenant IDOR check)

✓ Financial Rules Tested

✓ AI Service Contract Tested (if touching reconciliation)

✓ Error Handling Tested

✓ Coverage Threshold Met

✓ CI Passing

---

# REFERENCES

Coding Standards

docs/08_CODING_STANDARDS.md

Error Catalog

docs/09_ERROR_CATALOG.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Hybrid Architecture

docs/21_HYBRID_ARCHITECTURE.md

Financial Edge Cases

docs/22_FINANCIAL_EDGE_CASES.md

Implementation

implementation/

---

END OF DOCUMENT