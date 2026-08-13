# 21_HYBRID_ARCHITECTURE.md

# Ganaka Hybrid Architecture Specification

Version: 1.0.0

Status: Approved

Owner: Platform + AI

---

# PURPOSE

Ganaka intentionally uses TWO backend services, not one. This is a
deliberate architectural decision, not a contradiction and not a
migration-in-progress. This document is the single source of truth
for:

- Why the hybrid split exists
- Exactly which responsibilities belong to which service
- How the two services communicate
- How authentication works between them
- How failures, timeouts, retries, and degraded states are handled

If any other document (README.md, CLAUDE.md, implementation/00_FOUNDATION.md,
or any implementation/*.md file) appears to describe a single-backend
system, THIS document's OWNERSHIP_MATRIX and COMMUNICATION sections
win. Update the other document to match rather than assuming this
document is wrong.

---

# WHY HYBRID

The Core Platform (auth, workspace, billing, integrations, REST APIs)
is a stable, transactional, RBAC-heavy, audit-heavy domain. Spring
Boot's maturity in exactly this area (Spring Security, Spring Data
JPA, transaction management) is the right tool.

AI Reconciliation (fuzzy matching, confidence scoring, anomaly
detection, future ML models) is a fast-moving, experimentation-heavy
domain where Python's ML/data ecosystem (pandas, scikit-learn,
future PyTorch models) and FastAPI's async performance for
compute-bound matching workloads is the right tool.

Splitting them lets the AI matching logic evolve (new models, new
heuristics) independently of the transactional core, without forcing
either domain to compromise its tooling.

---

# THE TWO SERVICES

## CORE PLATFORM SERVICE (Spring Boot)

Owns

- Authentication (implementation/01_AUTHENTICATION.md)
- Authorization / RBAC (implementation/02_WORKSPACE_AND_RBAC.md)
- User Management (implementation/03_USER_MANAGEMENT.md)
- Workspace Management (implementation/02_WORKSPACE_AND_RBAC.md)
- Shopify Integration (implementation/04_SHOPIFY.md)
- Razorpay Integration (implementation/05_RAZORPAY.md)
- Finance Engine — canonical ledger, normalization (implementation/06_FINANCE_ENGINE.md)
- Reconciliation orchestration (NOT matching logic — see below)
- Dashboard, Reports, Notifications, Billing, Admin, Monitoring
- All public REST APIs (`/api/v1/*`)
- All background jobs and schedulers
- All audit logging
- The only service exposed to the internet / the frontend

## AI SERVICE (FastAPI)

Owns

- AI Reconciliation matching algorithm execution (implements the
  DISCREPANCY DECISION TABLE defined in
  implementation/07_RECONCILIATION_ENGINE.md)
- Confidence scoring for ambiguous matches
- Manual-review suggestions / ranking
- Anomaly detection (unusual settlement delay patterns, refund
  spikes, etc. — feeds docs/08_DASHBOARD.md INSIGHTS)
- Future ML models (fraud scoring, forecasting)

Does NOT own

- Any authentication of end users (it never sees a user-facing JWT)
- Any direct database writes to financial source-of-truth tables
  (orders, payments, settlements, ledger_entries) — read-only access
  only, see DATA_OWNERSHIP below
- Any public-facing endpoint — the AI Service is never reachable
  from the internet or the frontend directly, only from the Core
  Platform Service over the internal network

---

# OWNERSHIP_MATRIX

| Capability                          | Owner               |
|--------------------------------------|--------------------|
| Login / Session / JWT                | Core Platform       |
| Workspace / RBAC                     | Core Platform       |
| Shopify / Razorpay sync              | Core Platform       |
| Canonical ledger (FinancialTransaction) | Core Platform    |
| Reconciliation job creation, status, storage of results | Core Platform |
| Reconciliation MATCHING ALGORITHM    | AI Service          |
| Confidence score / suggestion ranking | AI Service         |
| Anomaly / insight generation         | AI Service          |
| Dashboard, Reports, Billing, Admin   | Core Platform       |
| Notifications                        | Core Platform       |

Rule: if a capability is not in this table, it defaults to Core
Platform. The AI Service's scope only ever grows by an explicit
addition to this table — never by inference.

---

# DATA_OWNERSHIP

- PostgreSQL is a single shared database instance/cluster.
- Core Platform Service holds write access to every table.
- AI Service holds READ-ONLY access, via a separate least-privilege
  database role (`ganaka_ai_readonly`) granted `SELECT` only on:
  `shopify_orders`, `razorpay_payments`, `razorpay_settlements`,
  `razorpay_settlement_payment`, `shopify_refunds`, `razorpay_refunds`,
  `financial_transactions`, `ledger_entries` (table names as defined
  in each owning module's DATABASE section — implementation/04_SHOPIFY.md,
  implementation/05_RAZORPAY.md, implementation/06_FINANCE_ENGINE.md).
- AI Service writes ONLY to its own tables, prefixed `ai_`:
  `ai_match_result`, `ai_confidence_score`, `ai_suggestion`,
  `ai_anomaly`, `ai_model_version`.
- Core Platform Service reads `ai_match_result` etc. back via its own
  DB role to persist final `reconciliation_results` — the AI
  Service's output is an input to Core Platform's canonical
  reconciliation record, never the record of truth itself. This
  keeps BR-014 ("Business calculations must never modify original
  imported records") and RULE DB-013 (immutable completed
  reconciliation) intact even though a second service is involved.

Validation

Reject any AI Service code path that executes `INSERT`, `UPDATE`, or
`DELETE` against any table not prefixed `ai_`.

---

# COMMUNICATION

Protocol

HTTPS, internal network only (AI Service has no public ingress —
enforce via cloud provider network policy / private service
networking, not just application-layer checks).

Direction

Core Platform Service → AI Service only. The AI Service never calls
back into Core Platform Service synchronously. If the AI Service
needs Core Platform data it doesn't already have read access to via
the shared database, it is added to DATA_OWNERSHIP's read grant list
above — it does not get a callback API.

Request Shape

`POST /internal/v1/reconcile`

```json
{
  "workspace_id": "uuid",
  "reconciliation_job_id": "uuid",
  "order_ids": ["uuid", "..."]
}
```

Response Shape

```json
{
  "reconciliation_job_id": "uuid",
  "results": [
    {
      "order_id": "uuid",
      "match_status": "MATCHED",
      "confidence": 0.98,
      "matched_payment_id": "uuid",
      "reason_code": null
    }
  ],
  "model_version": "matching-engine-2026.07.1"
}
```

Every AI Service response includes `model_version` — Core Platform
stores it alongside the reconciliation result for auditability and
reproducibility (ties to RULE BR-013: reconciliation must be
deterministic — a given `model_version` must always produce the
same output for the same input; if the AI Service iterates its
model, that becomes a new `model_version`, never a silent behavior
change under the same version string).

---

# AUTHENTICATION BETWEEN SERVICES

The AI Service never validates end-user JWTs and never sees them.

Core Platform Service authenticates to the AI Service using a
short-lived internal service token (JWT, 5-minute expiry, signed
with a separate `INTERNAL_SERVICE_JWT_SECRET`, distinct from the
user-facing `JWT_SECRET`), generated fresh per outbound call or
cached for at most 4 minutes.

Claims

```json
{
  "iss": "core-platform-service",
  "aud": "ai-service",
  "workspace_id": "uuid",
  "purpose": "reconciliation",
  "exp": 1234567890
}
```

AI Service validates: signature, issuer, audience, expiry. It never
needs to look up a user, role, or permission — workspace-scoping is
enforced entirely by the `workspace_id` claim, and the AI Service's
read-only DB queries always filter by that same `workspace_id`
(tenant isolation is preserved end-to-end, see docs/06_SECURITY_REQUIREMENTS.md
RULE SEC-007 — this internal call is not an exception to it).

Validation

Reject any AI Service endpoint that accepts a request without a
valid internal service token.

Reject any AI Service endpoint that accepts a `workspace_id` from
the request body without cross-checking it against the token's
`workspace_id` claim.

---

# FAILURE HANDLING

## Timeouts

Core Platform → AI Service call timeout: 30 seconds (matching runs
are expected to complete well within this for normal batch sizes;
see implementation/07_RECONCILIATION_ENGINE.md PERFORMANCE — 100,000
transactions / <10 minutes is an async batch target, not this
synchronous per-call timeout, which applies to a single job-status
call, not the whole batch — large batches are chunked, see BATCHING
below).

## Batching

For any `order_ids` list beyond 500, Core Platform splits into
multiple `POST /internal/v1/reconcile` calls, sequentially or with
bounded concurrency (max 5 in flight), rather than one large
synchronous call — keeps the 30s timeout meaningful at any repo scale.

## Retries

On timeout or 5xx from the AI Service: retry up to 3 times with
exponential backoff (2s, 4s, 8s). On the 4th failure, mark the
reconciliation job `FAILED` with `error.code = AI_SERVICE_UNAVAILABLE`,
enqueue for the existing reconciliation `RETRY_POLICY` (5 attempts,
exponential backoff — implementation/07_RECONCILIATION_ENGINE.md
AUTOMATION) rather than retrying inline indefinitely.

## Circuit Breaker

Core Platform maintains a circuit breaker around AI Service calls
(per RULE CODE rules: implement via a standard library, e.g. Resilience4j
— do not hand-roll). Thresholds:

- Open circuit after 5 consecutive failures within 1 minute.
- Half-open probe after 30 seconds.
- Close after 2 consecutive successes.

While circuit is open: new reconciliation job requests are queued
(not rejected) and processed once the circuit closes; existing
Dashboard/Reports keep serving the last-known reconciliation results
— they must never block on AI Service availability (ties to
implementation/08_DASHBOARD.md CURSOR_RULES: "Dashboard must remain
functional even if one service is unavailable" — this is precisely
the scenario that rule anticipates).

## Health Checks

AI Service exposes `GET /internal/v1/health` (no auth required, no
data returned beyond `{"status": "healthy"}`, internal-network-only
regardless). Core Platform's own `/api/v1/platform/health`
(implementation/11_PLATFORM.md) includes AI Service reachability as
one dependency check, surfaced as `DEGRADED` (not `UNAVAILABLE`) if
the AI Service is down, since Core Platform functions without it
for everything except running new reconciliation matches.

## Degraded Mode Behavior

If the AI Service is unavailable:

- New reconciliation runs queue rather than fail outright (see
  Circuit Breaker above).
- Existing reconciliation results, dashboards, reports remain fully
  available (read-only, from Core Platform's own database).
- A `SERVICE_DEGRADED` notification fires per
  implementation/10_NOTIFICATION_SYSTEM.md (priority HIGH) to
  workspace Admins/Owners if degraded state exceeds 15 minutes.

---

# DEPLOYMENT

Each service has its own Dockerfile, its own CI pipeline stage, and
deploys independently. A Core Platform deploy must never require an
AI Service deploy and vice versa — this is what makes the hybrid
split actually useful rather than just two repos glued together at
the hip. Contract compatibility between them is guarded by:

- `model_version` versioning (above) for behavior changes.
- API contract tests (docs/10_TESTING_STRATEGY.md — add AI Service
  contract tests as an explicit test suite, see that document's
  new WEBHOOK/API/AI TESTING additions) run in both services' CI
  against a shared, versioned request/response schema (this
  document's COMMUNICATION section is that schema's source of truth).

---

# OBSERVABILITY

Every cross-service call emits:

- A shared `correlation_id` (generated by Core Platform, passed to
  AI Service, included in both services' structured logs)
- Latency metric (`ai_service_call_duration_ms`)
- Outcome metric (`ai_service_call_result` = success/timeout/error)
- Circuit breaker state metric (`ai_service_circuit_state`)

These feed docs/16_MONITORING_AND_OBSERVABILITY.md dashboards and
alert rules (see that document's HYBRID_SERVICE_METRICS addition).

---

# CURSOR_RULES

Never implement AI Reconciliation matching logic inside the Core
Platform Service (Spring Boot) — it must call the AI Service.

Never implement authentication, RBAC, billing, or any Core Platform
capability inside the AI Service (FastAPI) — it must not duplicate
that logic even for convenience.

Never let the AI Service write to any table it doesn't own
(see DATA_OWNERSHIP).

Never let the frontend call the AI Service directly — always through
Core Platform Service's public API.

Always version AI Service model/algorithm changes via `model_version`,
never silently.

Always wrap AI Service calls in the circuit breaker — never a bare
HTTP call.

Always degrade gracefully — Core Platform must serve existing data
even when the AI Service is fully down.

---

# REFERENCES

Reconciliation Engine

implementation/07_RECONCILIATION_ENGINE.md

Foundation / Tech Stack

implementation/00_FOUNDATION.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Monitoring

docs/16_MONITORING_AND_OBSERVABILITY.md

---

END OF DOCUMENT
