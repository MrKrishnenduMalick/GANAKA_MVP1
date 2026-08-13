# GANAKA — ARCHITECTURE & SECURITY AUDIT

Audit type: **Read-only.** No code was modified, no patches generated, no refactors performed.
Reviewer role: Principal Software Architect / Senior Security Engineer.
Repository audited: `GANAKA-main.zip` (this is a **separate copy** of the codebase from the one reviewed in `MILESTONE1_REVIEW.md` — filenames, `.env`, and `CORS_ORIGINS` config differ and do **not** include that review's fix; findings here are independent and re-verified against this delivery).

**Important scope correction:** the repository actually contains Milestones 0–7 (Auth/Workspace, Shopify, Razorpay, Reconciliation, Dashboard, Reports/Notifications/Health, Frontend) per its own `PROJECT_STATUS.md`. This audit covers the full breadth requested, not just Milestone 1.

---

## Scores

Scores below are as originally assessed (pre-fix). See "FIX STATUS" further down for what changed after the remediation pass — scores were not recalculated for that pass since the brief was explicitly a fix task, not a re-audit; a fresh audit would be needed to assign updated scores with the same rigor.

| Dimension | Score (pre-fix) |
|---|---|
| 1. Overall architecture | **5.5/10** |
| 2. Security | **5/10** |
| 3. Scalability | **6/10** |
| 4. Maintainability | **4.5/10** |
| 5. Production readiness | **3.5/10** |

**Why these are lower than the Milestone 1 review's scores:** Milestone 1 (auth/workspace/RBAC) is genuinely strong (would score ~8.5/10 on its own — see `MILESTONE1_REVIEW.md`). Everything built on top of it (Shopify M2 onward) shows a sharp quality drop: a single god-module, several features that return success responses without doing the work they claim to do, and one integration (Razorpay) that cannot function correctly in a real multi-tenant deployment. The scores above are for the **repository as a whole**, and are pulled down by M2–M6.

---

## Top 20 Issues (severity-ordered)

1. **[CRITICAL]** Razorpay "connect" uses one global, deployment-wide credential for every workspace — not per-tenant OAuth/API keys. Every workspace that connects Razorpay ends up reading and re-storing the *same* merchant account's payments/refunds/settlements. Breaks multi-tenancy and cross-tenant confidentiality.
2. **[CRITICAL]** Reports/Exports feature is non-functional. Every `export_*` function returns a fabricated `download_url` (`/api/v1/exports/download/{filename}`) that has **no corresponding route** — no file is ever generated. `PROJECT_STATUS.md` marks this "✅ Complete."
3. **[CRITICAL]** Notification delivery is a stub. `send_notification()` only calls `logger.info(...)`; no email or webhook is ever sent, despite preferences UI/API and `PROJECT_STATUS.md` describing "email/webhook channels" as complete.
4. **[CRITICAL]** Settlement-mismatch detection ("Settlement Difference," a spec-required rule) is not a real payment↔settlement match — it's a workspace-wide heuristic ("if the workspace has *any* settlement record, treat *every* captured payment as settled"), self-documented in a code comment as a known gap. This directly contradicts the product's #1 principle (Correctness) and the "never guess financial values" rule.
5. **[CRITICAL]** Backend module boundary collapse: `backend/app/modules/shopify/` contains **seven** unrelated bounded contexts — Shopify, Razorpay, Reconciliation, Dashboard, Exports, Notifications, Health — in one `service.py` (2,282 lines, 74 functions) and one `router.py` (850 lines, 7 separately-prefixed `APIRouter` instances). This is not "the Shopify module doing a bit too much" — it is the entire backend business logic for Milestones 2–6 living inside a folder named `shopify`.
6. **[CRITICAL]** Cross-tenant Shopify webhook spoofing surface: `_verify_webhook_hmac` validates the payload against the single app-wide `SHOPIFY_API_SECRET` but never binds the HMAC to the claimed `shop_domain`, and idempotency dedup is keyed globally on `payload_hash` (not scoped by shop). An attacker who has ever obtained one valid `(payload, HMAC)` pair for their own connected shop (e.g., a free dev store) can resend it with a different `X-Shopify-Shop-Domain` header to inject that payload into a different workspace's `SHOPIFY_ORDER/PRODUCT/CUSTOMER` collections.
7. **[CRITICAL]** "Money At Risk" — one of the seven financial detection rules explicitly required by the product spec (`Detect: Ghost Orders · Missing Payments · Duplicate Payments · Amount Mismatch · Refund Mismatch · Settlement Difference · Money At Risk`) — has zero implementation anywhere in the codebase.
8. **[HIGH]** `POST /shopify/sync/incremental` contains real business logic and direct DB writes inside the **router**, contradicting the router file's own documented rule ("No business logic lives in controllers"). Worse, it's also a stub: it inserts a job doc with `status: RUNNING`, never processes anything, never updates that doc, yet the endpoint unconditionally returns `{"status": "COMPLETED"}` — the persisted job record and the API response permanently disagree.
9. **[HIGH]** Reconciliation results don't carry the five fields the spec requires for every result ("Evidence, Business Rule, Calculation, Explanation, Recommendation") — only a single free-text `reason` string. Every exception, regardless of type, gets the same hardcoded `suggested_action: "Review manually"` rather than a rule-specific recommendation. This weakens the product's #2/#3 principles (Transparency, Auditability).
10. **[HIGH]** Razorpay has no webhook receiver at all — `RAZORPAY_WEBHOOK_EVENT` has a provisioned collection and indexes in `db.py` but no route, no HMAC verification function, no processing logic exists anywhere. Razorpay data is only ever as fresh as the last manual `POST /razorpay/sync`, so reconciliation can silently run against stale payment/settlement state — inconsistent with Shopify's real-time webhook path.
11. **[HIGH]** `CORS_ORIGINS="*"` combined with `allow_credentials=True` is live in this repository's `backend/.env` and `server.py` (same class of issue independently found and fixed in the Milestone 1 review of a different copy of this repo — that fix is **not** present here). Any origin gets a credentialed cross-origin channel to the API.
12. **[HIGH]** `POST /shopify/webhooks/test` is a fully authenticated, production-reachable endpoint that runs attacker-controlled payload/topic/shop_domain through the real webhook processing pipeline. Bounded by needing a valid HMAC (mitigating factor), but there is no environment gating (e.g., debug-only flag) keeping a "test" endpoint out of the production API surface.
13. **[HIGH]** Dashboard endpoints issue many sequential, un-batched MongoDB round trips per request instead of using `asyncio.gather()` or a single aggregation. `get_dashboard_overview` alone performs 4 aggregate pipelines + 9 `count_documents` calls serially; a full dashboard page load (which also calls the separate revenue/orders/payments/refunds/settlements/exceptions/match-rate/analytics endpoints) compounds this into dozens of sequential queries. Will not scale gracefully even at the target 10–50 customers if any one workspace has meaningful data volume.
14. **[MEDIUM]** `RECONCILIATION_MATCH_STATUSES` (the declared status taxonomy) doesn't match what the matcher function actually returns: it's missing `GHOST_ORDER` (which the matcher does return) and includes `UNMATCHED`/`MISSING_ORDER` (which the matcher never returns). The constant is unused elsewhere in the codebase — dead, inaccurate documentation-as-code that will mislead the next engineer who trusts it.
15. **[MEDIUM]** `client_ip()` (rate limiting) trusts `X-Forwarded-For` unconditionally with no trusted-proxy configuration; spoofable if the API is ever exposed directly. (Carried over from Milestone 1 review — same file, unchanged.)
16. **[MEDIUM]** `_build_export_query`'s `shop_domain` filter branch sets `query["workspace_id"] = None` to mean "no results" when the shop isn't found for the workspace — an unconventional and fragile way to express "return nothing" (works today only because no document has `workspace_id: None`, but it's a landmine for future filter logic reuse).
17. **[MEDIUM]** No idempotency/duplicate-prevention gap in `run_razorpay_sync`: unlike `run_reconciliation` (which has an idempotency key) and Shopify webhooks (payload hash dedup), a user re-clicking "Sync" simply re-runs three full syncs back-to-back with no lock or debounce — wasteful of Razorpay API quota, and if payments/refunds/settlements APIs paginate inconsistently between the three sequential calls, could produce a subtly inconsistent snapshot.
18. **[MEDIUM]** Frontend/backend module-boundary asymmetry: the React frontend is well organized (`pages/shopify`, `pages/razorpay`, `pages/reconciliation`, `pages/reports`, `pages/notifications`, `pages/settings` as separate folders) while the backend crams the equivalent surface into one module. This means the API's structure actively misleads consumers of its own OpenAPI docs about where functionality "lives," and any future backend engineer will have a much harder time finding code than the frontend suggests they should.
19. **[LOW]** `errors.py`'s validation handler assigns the HTTP status int to a variable literally named `code` before passing it positionally where `_envelope` expects `status_code` — functionally correct, confusing to read. (Carried over from Milestone 1 review.)
20. **[LOW]** No TTL indexes on `email_verification_token`, `password_reset_token`, `workspace_invitation`, or the newer `shopify_oauth_state` collection — expired rows accumulate indefinitely (the milestone-2+ code repeats the same omission pattern already flagged for Milestone 1).

---

## Detailed Findings by Requested Dimension

### 1. Folder structure
Top-level layout (`backend/app/{core,modules,services}`, `frontend/src/{pages,components,context,lib}`, `docs/`, `implementation/`, `tests/`) is conventional and reasonable. The problem is not the top-level layout — it's what got placed *inside* `backend/app/modules/shopify/` (see #5 above and "Module Boundaries" below).

### 2. Module boundaries — **the central finding of this audit**
`backend/app/modules/` has exactly four folders: `auth`, `rbac`, `workspace`, `shopify`. Everything built after Milestone 1 (Razorpay, Reconciliation, Dashboard, Exports, Notifications, Health) was added into the `shopify` folder rather than getting its own module, even though `router.py` mounts them as seven independently-prefixed routers (`/shopify`, `/razorpay`, `/reconciliation`, `/dashboard`, `/exports`, `/notifications`, `/health`) and even carries a docstring explicitly listing which milestone each section belongs to — the author(s) clearly knew these were separate concerns and chose not to separate the files. Answering your direct questions:
- **"Is too much functionality implemented inside the shopify module?"** Yes — dramatically. It contains roughly 85% of the entire backend's business logic (2,282 of ~3,500+ total service-layer lines).
- **"Should Razorpay, Dashboard, Reconciliation, Reports and Notifications exist as separate modules?"** Yes. Each already has its own DB collections, its own router prefix, its own permission namespace (`razorpay.*`, `dashboard.*`, etc.), and no shared internal state with Shopify beyond read access to Shopify order data (which reconciliation needs and could get via a clean cross-module service call, same as it already does for Razorpay data). There is no technical reason they're colocated.
- **"Is the current architecture maintainable?"** Not in its current form for these modules. A 2,282-line, 74-function single file with seven distinct feature areas is a merge-conflict and code-review bottleneck, defeats IDE navigation, and makes "reuse existing services, never duplicate business logic" (the project's own engineering rule) hard to verify by inspection — you have to read the whole file to know if something already exists.

### 3. Backend architecture
FastAPI + Motor (async MongoDB), Pydantic v2 schemas, JWT auth — consistent stack, no ORM confusion. The `core/` layer (config, db, deps, errors, security, crypto, audit, rate_limit, pagination, models) is well-factored and is reused correctly by every module including the new ones. The controller/service/schema split is *followed in principle* but *violated in practice* at the one router endpoint noted in #8. Auth-layer architecture (from Milestone 1) remains a high point of the codebase.

### 4. Frontend architecture
React 19 (CRA/CRACO), feature-folder organization under `pages/`, shared `lib/api.js` axios-style client, `AuthContext` for session state, shadcn/ui + Tailwind. Structurally healthier than the backend for the same feature set (see #18). Not deeply audited beyond structure in this pass since the backend defects (stub exports/notifications, broken Razorpay multi-tenancy) mean the frontend is necessarily consuming APIs that don't do what their names promise, regardless of frontend code quality.

### 5. Authentication
Unchanged from, and consistent with, the Milestone 1 review: bcrypt, hashed opaque tokens, httpOnly/Secure/SameSite=Strict refresh cookie, session idle+absolute expiry, account lockout, Google ID token audience/issuer checks. No new auth code was introduced in M2–M6 (correctly reused). See `MILESTONE1_REVIEW.md` for full detail; not re-litigated here except where a new module regresses it (it doesn't).

### 6. RBAC
`require_permission(...)` dependency is applied consistently across every new M2–M6 endpoint (`shopify.connect`, `razorpay.connect`, `finance.read`, `dashboard.read`, `workspace.read`, etc.) — this pattern held up well as the surface area grew 5x. No endpoint found that skips permission enforcement.

### 7. Workspace isolation
Every M2–M6 query in `service.py` scopes by `workspace_id` derived from `context` (never from client input) — this discipline, established in Milestone 1, was carried forward correctly for query filtering. The one place it meaningfully breaks down is **data provenance, not query scoping**: Razorpay's shared global credential (#1) and the webhook spoofing surface (#6) both mean a workspace can end up *containing* another party's data even though every read query still correctly filters by its own `workspace_id`. Isolation-by-query is intact; isolation-by-data-origin is not.

### 8. Shopify integration
The best-implemented external integration in the repo: real per-shop OAuth (install → HMAC-verified callback → single-use state nonce → token exchange → shop verification → AES-256-GCM encrypted storage), idempotent full sync (`upsert` by `(workspace_id, shopify_id)`), and webhook-driven incremental sync with HMAC verification and payload-hash dedup. Weaknesses: the dedup/HMAC scheme isn't shop-scoped (#6), and the `/webhooks/test` endpoint (#12) shouldn't be reachable in production.

### 9. Razorpay integration
The weakest integration by far. No per-tenant credential capture — `connect_razorpay` takes no request body and simply copies `settings.RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` from the deployment's own environment into every workspace that calls it (#1). No webhook receiver despite provisioned DB schema for one (#10). No idempotency guard on manual sync (#17). This integration cannot serve real, independent D2C merchants in its current form — it can only ever reflect one Razorpay account, platform-wide.

### 10. Reconciliation engine
Core matching logic (`_match_status_for_order`) is readable and does implement gateway eligibility filtering, duplicate detection, ghost-order detection, missing-payment detection, and refund-mismatch detection reasonably faithfully to the spec's decision table. Two real correctness gaps: settlement matching is a heuristic, not a real match (#4), and "Money At Risk" isn't computed at all (#7). Job idempotency (via `idempotency_key`) is a good pattern, correctly implemented.

### 11. Dashboard
Functionally reasonable (revenue/orders/payments/refunds/settlements/match-rate/exceptions/analytics endpoints all exist and query real, workspace-scoped data), but performance is a real concern (#13) — every card issues its own sequential round trip rather than batching or precomputing.

### 12. Reports
Not implemented — see #2. This is the most clear-cut "claimed without evidence" finding in the audit: the code, the docstrings, the OpenAPI descriptions ("Returns a download URL"), and `PROJECT_STATUS.md` all describe a working CSV/Excel/PDF export feature; none of it exists past a fabricated URL string.

### 13. Notification system
Preferences get/update are real and correctly persisted per-workspace. Actual delivery is not implemented — see #3.

### 14. Database schema
Consistent conventions carried from Milestone 1: every collection has `created_at`/`updated_at`/`deleted_at` (soft delete), `workspace_id` scoping on every tenant-owned collection, encrypted-at-rest credential fields (`*_encrypted`) never returned in DTOs. The one schema-vs-reality drift is the unused `RAZORPAY_WEBHOOK_EVENT` collection (#10) and the inaccurate `RECONCILIATION_MATCH_STATUSES` constant (#14 in the issue list).

### 15. MongoDB indexes
`db.bootstrap()` continues the idempotent additive-index pattern from Milestone 1 and adds sensible indexes for the new collections (`(workspace_id, shop_domain)`, `(workspace_id, shopify_id)` uniqueness for orders/products/customers, `(workspace_id, razorpay_id)` for payments/refunds/settlements, `idempotency_key` uniqueness for reconciliation jobs). Gap: no TTL index on `shopify_oauth_state` (short-lived, single-use nonces) mirroring the same omission already flagged for the auth-token collections in Milestone 1 (#20).

### 16. API routes
REST conventions are followed (resource nouns, correct HTTP verbs/status codes, consistent pagination via `page/page_size/sort` query params). The routing *organization* (all seven routers defined in one file) is the architectural issue already covered in #5, not a REST-convention issue — the URLs themselves (`/api/v1/razorpay/...`, `/api/v1/dashboard/...`, etc.) are clean and would look identical to a client regardless of how the server code is filed.

### 17. React routing
Not re-audited in depth this pass (structure alone was reviewed, see #4/#18); no obvious anti-patterns in the folder layout.

### 18. Error handling
Canonical error envelope (`timestamp/status/code/message/path/requestId`) from Milestone 1 is reused consistently by the new modules (`AppError("SHOPIFY-xxx")`, `AppError("RAZORPAY-xxx")`, etc. all route through the same handler). Good consistency at scale.

### 19. Security
See OWASP section below for the structured pass. Net position: strong foundation (Milestone 1) undermined by two integration-specific issues (#1, #6) that are more severe than anything found in Milestone 1's own review, plus a recurrence of the CORS misconfiguration (#11) that was already caught and fixed in a sibling copy of this repo but not here.

### 20. Performance
Encryption/decryption (AES-GCM) is cheap and not a concern. The real performance risk is #13 (dashboard query fan-out) and, secondarily, `run_reconciliation` processing orders one-at-a-time with an `insert_one` per result/exception inside a Python loop rather than batching with `insert_many` — fine at MVP scale (10–50 customers, bounded order volume) but worth flagging as a scaling ceiling, not an immediate problem.

### 21. Deployment readiness
Not production-ready as delivered: exports and notifications are non-functional (#2, #3), Razorpay cannot onboard real independent merchants (#1), and the CORS misconfiguration is live in the shipped `.env` (#11). `PROJECT_STATUS.md` also still carries the pre-existing, self-disclosed, unresolved stack conflict (spec docs call for Next.js/Spring Boot/PostgreSQL/Redis/Flyway and explicitly forbid MongoDB, while the running repo is FastAPI/Mongo/React) — flagged here again only because it remains an open Critical decision for the product owner per the repository's own source-of-truth rule, not because this audit is re-discovering it.

---

## OWASP Top 10 / Focused Security Pass

| Area | Finding |
|---|---|
| **A01 Broken Access Control** | RBAC/tenant-scoping is consistently enforced at the query layer (see "Workspace isolation" above). The exception is the webhook spoofing path (#6), which is an access-control failure at the *data-origin* layer rather than the query layer. |
| **A02 Cryptographic Failures** | AES-256-GCM for credential-at-rest (Shopify token, Razorpay key) is correctly implemented with random nonces and authenticated encryption; JWT uses HS256 with a required (non-defaulted) secret. No findings here. |
| **A03 Injection** | No raw query string interpolation found; Mongo queries are built as dicts, sort fields are allow-listed (`pagination.py`). No SQL/NoSQL injection vectors identified in the reviewed code. |
| **A04 Insecure Design** | The Razorpay shared-credential model (#1) and the exports/notifications stubs (#2, #3) are insecure/incomplete *by design*, not by implementation bug — these are the audit's headline design-level findings. |
| **A05 Security Misconfiguration** | `CORS_ORIGINS="*"` + `allow_credentials=True`, live in `.env` (#11). |
| **A06 Vulnerable/Outdated Components** | Not assessed — no network access in this environment to check installed package versions against current CVE feeds; `requirements.txt`/`package.json` were not diffed against an advisory database. |
| **A07 Identification & Authentication Failures** | No regressions found in M2–M6; Milestone 1's auth remains intact and is reused correctly by every new endpoint via `require_permission`. |
| **A08 Software & Data Integrity Failures** | Webhook HMAC verification exists for Shopify but isn't shop-scoped (#6); Razorpay has no webhook integrity check at all because it has no webhook endpoint (#10). |
| **A09 Security Logging & Monitoring Failures** | Audit trail (`audit.record(...)`) is called consistently for connect/disconnect/sync/reconciliation/webhook events across every new module — this is a genuine strength carried forward from Milestone 1. |
| **A10 Server-Side Request Forgery** | `_exchange_code`/`_verify_shop`/`_razorpay_get` all call fixed, hardcoded external hosts (`{shop}` is validated indirectly via the OAuth HMAC/state flow before being used in a URL) — no user-controlled arbitrary-URL fetch found. |

**Additional focused checks requested:**
- **Multi-tenant isolation:** Query-level isolation is solid; data-provenance isolation is broken for Razorpay (#1) and partially exposed for Shopify webhooks (#6).
- **JWT:** Unchanged from Milestone 1 — algorithm pinned, secret required from env, no `alg: none` acceptance risk observed.
- **Secrets:** All required secrets (`JWT_SECRET`, `MONGO_URL`, `ENCRYPTION_KEY`, `SHOPIFY_API_SECRET`, `RAZORPAY_KEY_SECRET`) are read via `os.environ[...]` (hard failure if missing) rather than defaulted — good practice, consistent with Milestone 1.
- **Encryption:** AES-256-GCM, correctly implemented (see A02).
- **Webhook verification:** Shopify — implemented but not shop-scoped (#6). Razorpay — does not exist (#10).
- **Rate limiting:** `enforce(...)` is called on every state-changing M2–M6 endpoint, consistent with the Milestone 1 pattern; the underlying `client_ip()` trust issue (#15) applies here too since it's shared infrastructure.
- **Audit logging:** Comprehensive and consistent across all new modules (see A09).

---

---

## FIX STATUS (post-remediation pass)

The Critical and High findings above were remediated in a follow-up engineering
pass. Full detail, file-by-file, is in `FIX_SUMMARY.md`; this section updates
the status of each finding inline so this document stays the source of truth
for "what's actually true about this repo today."

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | CRITICAL | Razorpay shared global credential | **Fixed** — per-workspace `key_id`/`key_secret`/`webhook_secret`, verified against the live API, encrypted at rest. |
| 2 | CRITICAL | Exports non-functional | **Fixed** — real CSV/Excel/PDF generation, real `GET /exports/download/{filename}`, workspace-scoped, 24h TTL. |
| 3 | CRITICAL | Notifications stub | **Fixed** — real email (existing SMTP service) and webhook (HTTP POST) delivery, logged, wired into the Shopify sync-failure path. |
| 4 | CRITICAL | Settlement matching heuristic | **Improved, not fully solved** — now a per-payment time-window check instead of a workspace-wide static flag. True per-payment certainty still requires Razorpay's Settlement Recon API (not integrated). See FIX_SUMMARY §Accepted Risks. |
| 5 | CRITICAL | Module boundary collapse (god module) | **Deferred, by explicit instruction** — the remediation brief prohibited splitting `modules/shopify` into new folders unless absolutely required, and every other Critical fix was achievable in place. Still an accepted architectural risk. |
| 6 | CRITICAL | Cross-tenant webhook spoofing | **Improved, partially mitigated** — dedup now scoped per-shop (was a real cross-tenant data-loss bug, now fixed outright); added a payload/header consistency check for order-topic webhooks. Residual risk remains for topics without an embedded domain field — inherent to Shopify's shared-secret webhook design, not something Ganaka's server code alone can fully close. |
| 7 | CRITICAL | Money At Risk missing | **Fixed** — new `get_money_at_risk()` aggregation, `GET /dashboard/money-at-risk`, folded into the overview card. |
| 8 | HIGH | `incremental_sync` stub + logic in controller | **Fixed** — moved to `service.run_incremental_sync()`, real work performed, job doc always matches the API response. |
| 9 | HIGH | Missing Evidence/Business Rule/Calculation/Explanation/Recommendation fields | **Fixed** — added to every reconciliation result and exception (additive schema fields). |
| 10 | HIGH | No Razorpay webhook receiver | **Fixed** — `POST /razorpay/webhooks`, tenant resolved by per-connection secret match, deduped, processed. |
| 11 | HIGH | CORS wildcard + credentials | **Fixed** — same remediation as the sibling Milestone-1-only repo: refuses wildcard, falls back to `APP_BASE_URL`, fails closed. |
| 12 | HIGH | `/webhooks/test` reachable in prod | **Fixed** — 404s unless `ENABLE_TEST_ENDPOINTS=true` and `ENVIRONMENT != production`. |
| 13 | HIGH | Dashboard N+1 queries | **Fixed** — `get_dashboard_overview`'s 13 independent queries now run via `asyncio.gather`. |

Two bugs were discovered *while implementing these fixes* that were not in the
original Top 20 (this audit missed them on the first pass) but were blocking
or directly adjacent to Critical #1/#8, so they were corrected as a necessary
dependency of those fixes rather than left broken:

- **`RAZORPAY-*` error codes were raised throughout the code but never
  registered in `ERROR_REGISTRY`** — every Razorpay error path crashed with
  a raw `KeyError` instead of returning a proper HTTP response. Registered.
- **`razorpay_connection`'s unique index made reconnect-after-disconnect
  impossible** (unique on `workspace_id` across all statuses, not just
  `ACTIVE`) — contradicted `disconnect_razorpay()`'s own docstring promise.
  Fixed for Razorpay via a partial unique index. **The identical pattern
  still exists on `shopify_connection` and was left unfixed** (out of the
  approved scope for this pass) — see FIX_SUMMARY.
- **`httpx`, `openpyxl`, and `reportlab` were used/newly-required by the
  code but absent from `requirements.txt`** — `pip install -r
  requirements.txt` would not have installed what the code actually needs.
  Added.

Medium and Low findings from the original Top 20 were explicitly out of
scope for this pass and remain open.

## What the original audit did **not** do
Per the instructions for that task: no code was changed, no patches were written, and no refactor was performed or proposed as a diff. That document was observational only. Verification was static (full read-through of every backend module referenced above, `db.py` index bootstrap, and `server.py`/`router.py` wiring) plus `grep`-based cross-checks (e.g., confirming the absence of a `/download` route, a Razorpay webhook route, and any use of `RECONCILIATION_MATCH_STATUSES`). No backend process was started and no test suite was executed in that pass — it was a **static architecture and code audit**, not a runtime verification (the same network-access limitation noted in `MILESTONE1_REVIEW.md` applies here, and to the remediation pass documented above — see `FIX_SUMMARY.md` for what was and wasn't verifiable in this sandbox).
