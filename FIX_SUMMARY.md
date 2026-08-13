# FIX SUMMARY — Ganaka Post-Audit Remediation Pass

Date: 2026-08
Source of truth for this pass: `ARCHITECTURE_AUDIT.md`
Scope: all 7 Critical findings and all 6 High findings from that audit. No Medium/Low findings were
in scope. No architecture redesign, no module folder split, no database migration beyond additive/
idempotent index changes, no new technologies beyond what the audited code already imported or
required to do what it claimed.

---

# Executive Summary

`ARCHITECTURE_AUDIT.md` found 7 Critical and 6 High severity issues in the Ganaka MVP repository.
The two most severe were structural: Razorpay shared one platform-wide credential across every
tenant (a real multi-tenant confidentiality defect, not a theoretical one), and the entire Reports/
Exports feature returned a fabricated download URL that pointed at nothing — both had been marked
"✅ Complete" in `PROJECT_STATUS.md` and "Ready for Production Deployment" in
`FINAL_RELEASE_REPORT.md` before the audit caught them.

All 7 Critical and all 6 High findings have been fixed in this pass. The fixes were made in place,
inside the existing `modules/shopify` package structure, without splitting it into new folders
(per explicit instruction), without introducing new infrastructure, and without changing any API
contract except the one place a contract change was structurally unavoidable (`POST /razorpay/
connect` now requires a credential body, because the entire defect being fixed was that it
previously took none).

Two additional bugs were discovered while implementing these fixes — not on the original Top 20,
but directly blocking Critical #1 and #8 — and were corrected as a necessary dependency of those
fixes: `RAZORPAY-*` error codes were raised throughout the code but never registered, so every
Razorpay error path crashed with a raw `KeyError`; and `httpx`/`openpyxl`/`reportlab` were used (or
newly required) by the code but absent from `requirements.txt`.

**Bottom line:** backend and frontend implementation are code-complete, and the Critical/High
findings are remediated in the source. None of this has been exercised against a live external
system in this sandbox (no network access) — real Shopify, Razorpay, SMTP, and deployment testing
are still required before production use. See § Manual Testing Required and § Final Repository
Status below.

---

# Critical Issues Fixed

### C1 — Razorpay shared a single platform-wide credential across every tenant
**Before:** `connect_razorpay` read `settings.RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` from
deployment-wide environment variables and stored the same values for every workspace that called
it. Every tenant that connected Razorpay ended up reading and re-storing the same merchant
account's payments/refunds/settlements.
**After:** `POST /razorpay/connect` now requires `key_id`/`key_secret`/optional `webhook_secret` in
the request body. Credentials are verified against the live Razorpay API
(`_verify_razorpay_credentials`) before being accepted, then encrypted at rest (AES-256-GCM,
existing `crypto` module, unchanged) and stored per-workspace. No code path reads a global Razorpay
credential to service a tenant request any more.
**Discovered while fixing this:** `RAZORPAY-005/006/008/009` were raised throughout `service.py` but
never registered in `ERROR_REGISTRY` — every failure path crashed with an unhandled `KeyError`
instead of a real HTTP response. Registered (`RAZORPAY-005..009`). Also: the old unique index on
`razorpay_connection.workspace_id` (all statuses) made reconnecting after a disconnect impossible,
contradicting `disconnect_razorpay()`'s own docstring. Changed to a partial unique index scoped to
`status: ACTIVE`.

### C2 — Reports/Exports were entirely non-functional
**Before:** every `export_*` function returned a fabricated `download_url` string
(`/api/v1/exports/download/{filename}`) with no corresponding route and no file ever generated.
**After:** real CSV (stdlib `csv`), Excel (`openpyxl`), and PDF (`reportlab`) generation. Generated
files are stored in a new `export_file` collection (workspace-scoped, 24h TTL) and served by a real
`GET /exports/download/{filename}` route that checks the requesting workspace owns the file before
returning it. The three writers were smoke-tested standalone in this sandbox and confirmed to
produce real, non-trivial file bytes (44 / 4886 / 1469 bytes for a 1-row sample across CSV/XLSX/
PDF respectively).

### C3 — Notification delivery was a stub that always reported success
**Before:** `send_notification()` called `logger.info(...)` and nothing else, regardless of
preferences.
**After:** real email delivery via the existing SMTP-backed `email_service.send()` (new
`WORKSPACE_NOTIFICATION` template, sent to the workspace owner's registered address) and real
webhook delivery via `httpx.post()` to the configured `webhook_url`. Every attempt is logged to a
new `notification_delivery_log` collection with an honest status (`SENT` / `FAILED` /
`PENDING_NO_TRANSPORT` per channel; overall `sent` / `pending_no_transport` / `failed` / `skipped`).
If neither channel is configured, or the notification type is disabled in preferences, the function
returns a clearly-labeled `skipped` result rather than a fake success. Wired into the Shopify
sync-failure path (`failed_shopify_sync` preference) so it is a reachable code path, not just
implemented-but-never-called.

### C4 — Settlement matching was a workspace-wide static heuristic
**Before:** "if the workspace has any settlement record at all, treat every captured payment as
settled" — a payment from long before any settlement existed would be marked settled purely because
a settlement happened to exist *today*, anywhere in the workspace.
**After:** `_settled_within_window()` checks whether a settlement occurred within
`settlement_match_window_days` of that specific payment's own capture date. This is a materially
more accurate heuristic. **It is still a heuristic, not a fix that reaches full correctness** — true
per-payment linkage requires Razorpay's Settlement Recon API, which is not integrated (would be new
external-integration scope, out of bounds for this pass). Documented explicitly in the code and in
§ Remaining Accepted Risks below.

### C5 — Backend module boundary collapse (the "god module")
**Status: Deferred, by explicit instruction.** `modules/shopify` still contains Shopify, Razorpay,
Reconciliation, Dashboard, Exports, Notifications, and Health in one package. Every other Critical
fix was achievable in place; this one specifically requires restructuring into new folders, which
every remediation-pass brief explicitly prohibited ("Do NOT split the shopify module into separate
folders"). This remains an open, documented architectural risk — see § Remaining Accepted Risks.

### C6 — Cross-tenant Shopify webhook isolation
**Before:** webhook idempotency dedup was keyed on a global `payload_hash` — an identical payload
arriving for a *different* shop would be silently treated as a duplicate of the first shop's event
and dropped (a real cross-tenant data-loss bug, not just a security nicety). Separately, the HMAC
verification (correctly, per Shopify's own design) uses a single app-wide secret, so a valid
`(payload, HMAC)` pair captured from one connected shop could in principle be replayed with a
different `X-Shopify-Shop-Domain` header.
**After:** dedup is now scoped to `(shop_domain, payload_hash)`, which fully fixes the data-loss bug.
For the spoofing concern, added `_payload_shop_domain_consistent()`: for order-topic webhooks, the
payload's own embedded `order_status_url` is cross-checked against the claimed `shop_domain` header
and rejected on mismatch. **This is a partial mitigation, not a complete fix** — topics whose
payload carries no embedded domain field (some product/customer payloads) remain reliant on
Shopify's own delivery-time trust, which is inherent to Shopify's shared-secret webhook design and
cannot be fully closed from Ganaka's server code alone.

### C7 — "Money At Risk" was entirely unimplemented
**Before:** zero references anywhere in the codebase, despite being one of the seven financial
detection rules named explicitly in the product spec.
**After:** `get_money_at_risk()` aggregates the amount tied up in `OPEN` reconciliation exceptions,
broken down by exception type. Exposed via `GET /dashboard/money-at-risk` and folded into the
dashboard overview card as `money_at_risk` (additive field).

---

# High Issues Fixed

### H8 — `incremental_sync` was a stub with business logic in the controller
**Before:** the router directly inserted a `RUNNING` job document, never processed anything, never
updated that document, and unconditionally returned `{"status": "COMPLETED"}` — the persisted job
state and the API response permanently disagreed. This also violated the module's own documented
rule ("No business logic lives in controllers").
**After:** moved to `service.run_incremental_sync()`. There is no delta/cursor-based change feed
implemented anywhere in this codebase, so "incremental" honestly re-runs the same idempotent,
upsert-by-`shopify_id` full sync that `run_sync()` uses, rather than claiming a fake delta. The
persisted job document and the returned API response always match. The router is now a thin
validate-and-delegate call.

### H9 — Reconciliation results missing required explainability fields
**Before:** only a single free-text `reason` string; every exception got the same hardcoded
`suggested_action: "Review manually"` regardless of type.
**After:** `_match_status_for_order` returns a full dict with `evidence` / `business_rule` /
`calculation` / `explanation` / `recommendation`, built from `_BUSINESS_RULES` and
`_RECOMMENDATIONS` lookup tables keyed by match status. Persisted on every result; exceptions now
get a rule-specific `suggested_action`. Schema fields are additive/optional — existing clients
parsing `ReconciliationResultResponse` are unaffected.

### H10 — No Razorpay webhook receiver existed
**Before:** `RAZORPAY_WEBHOOK_EVENT` had a provisioned collection and indexes in `db.py`, but no
route, no signature verification, no processing logic anywhere. Razorpay data was only ever as
fresh as the last manual sync.
**After:** `POST /razorpay/webhooks`. Razorpay payloads carry no per-tenant identifier the way
Shopify's `X-Shopify-Shop-Domain` header does, and each workspace now has its own webhook secret
(per C1), so the tenant is resolved by testing each active connection's own secret against the
signature (`_resolve_razorpay_workspace`) — an O(active connections) scan, documented as acceptable
at the product's stated 10–50 customer scale. Deduped per-workspace, processed into the existing
payment/refund/settlement collections via the existing `_upsert_razorpay_many` helper (no schema
change).

### H11 — CORS wildcard combined with credentialed requests
**Before:** `CORS_ORIGINS="*"` live in `backend/.env`, combined with `allow_credentials=True` in
`server.py` — any origin could get a credentialed cross-origin channel to the API. `server.py` also
read `CORS_ORIGINS` independently of the (unused) `settings.CORS_ORIGINS`, a second, divergent copy
of the same logic.
**After:** `config.py` resolves `CORS_ORIGINS` once, refuses to honor `*` when credentials are
enabled, falls back to the deployment's own declared `APP_BASE_URL`, and fails closed (empty origin
list + warning log) if neither is usable. `server.py` now consumes `settings.CORS_ORIGINS` only.

### H12 — `/shopify/webhooks/test` reachable in production
**Before:** a fully authenticated endpoint that replays arbitrary payloads through the real webhook
pipeline, with no environment gating keeping it out of production.
**After:** returns 404 unless `ENABLE_TEST_ENDPOINTS=true` and `ENVIRONMENT != "production"` (both
new, explicit settings — default is disabled/production).

### H13 — Dashboard overview issued 13 sequential Mongo round trips
**Before:** `get_dashboard_overview` awaited 4 aggregate pipelines + 9 `count_documents` calls one
at a time.
**After:** all 13 independent queries (now 14, including the new Money At Risk aggregation) run
concurrently via `asyncio.gather`, bounding latency by the slowest single query instead of the sum
of all of them.

---

# Files Modified

Full detail with per-file reasoning is in `FILES_CHANGED.md`. Summary:

**Backend:** `app/core/config.py`, `app/core/errors.py`, `app/core/db.py`, `app/core/rate_limit.py`,
`server.py`, `app/services/email.py`, `app/modules/shopify/schemas.py`,
`app/modules/shopify/service.py`, `app/modules/shopify/router.py`, `requirements.txt`.

**Frontend:** `frontend/src/pages/razorpay/Connect.js` (credential form, required by the C1 contract
change), `frontend/src/pages/reports/Export.js` (now actually downloads the file the C2 fix
generates).

**Documentation:** `ARCHITECTURE_AUDIT.md`, `IMPLEMENTATION_REPORT.md`, `PROJECT_STATUS.md`,
`FILES_CHANGED.md`, `FINAL_RELEASE_REPORT.md`, and this file.

No other files were modified. No module was split into a new folder. No database migration script
was written (MongoDB has no DDL; all index changes are additive/idempotent via the existing
`db.bootstrap()` pattern, consistent with how the repository already handles schema changes).

---

# API Contract Changes

Only one breaking change was made, and it was structurally unavoidable:

- **`POST /razorpay/connect` now requires a JSON body** (`key_id`, `key_secret`, optional
  `webhook_secret`) where it previously took none. The entire defect being fixed (C1) was that this
  endpoint took no tenant-specific input at all — there is no way to make Razorpay genuinely
  multi-tenant without asking each tenant for their own credentials. The frontend was updated to
  match (`pages/razorpay/Connect.js`).

Everything else is either a new addition or additive-only:

- **New endpoints** (did not exist before, so cannot break an existing client): `POST /razorpay/
  webhooks`, `GET /exports/download/{filename}`, `GET /dashboard/money-at-risk`.
- **`POST /shopify/sync/incremental`** — same request/response shape as before; only the behavior
  behind it changed (from a lying stub to real work).
- **`DashboardOverviewResponse`** gained one additive, optional field: `money_at_risk` (defaults to
  `0.0`).
- **`ReconciliationResultResponse`** gained five additive, optional fields: `evidence`,
  `business_rule`, `calculation`, `explanation`, `recommendation`.
- **Export format values are unchanged** (`csv` / `excel` / `pdf`, matching the pre-existing
  `ExportRequest.format` pattern) — internally, `"excel"` now maps to a real `.xlsx` file rather
  than an extension-less placeholder, but the API-facing value a client sends is identical to before.

---

# Remaining Accepted Risks

These were explicitly out of scope for this pass (Medium/Low findings, or Critical/High findings
whose full resolution requires new infrastructure or a module split that was explicitly prohibited):

1. **Backend module boundary collapse (C5)** — `modules/shopify` still contains 7 unrelated bounded
   contexts in one package. Deferred by explicit instruction, not because it's low-risk.
2. **Settlement matching is still a heuristic (C4, improved not solved)** — true per-payment
   certainty requires Razorpay's Settlement Recon API, not integrated.
3. **Shopify webhook spoofing mitigation is partial (C6)** — closed for order-topic payloads that
   carry an embedded domain field; not closed for topics that don't. Inherent to Shopify's
   shared-secret webhook design.
4. **`client_ip()` trusts `X-Forwarded-For` unconditionally** (Medium, audit #15) — spoofable if the
   API is ever exposed without a trusted reverse proxy in front of it. Not touched.
5. **No idempotency guard on manual Razorpay sync** (Medium, audit #17) — re-clicking "Sync" re-runs
   three full API calls with no lock/debounce. Not touched.
6. **The identical "can't reconnect after disconnect" index bug found and fixed for
   `razorpay_connection` also exists on `shopify_connection`** — discovered as a side effect of
   fixing C1, but Shopify's connect/disconnect flow was not itself a named Critical/High finding, so
   it was left unfixed. **This is a real, reachable bug**: a workspace that disconnects Shopify can
   never reconnect it. Flagged here for prioritization, not fixed in this pass.
7. **No TTL indexes on `email_verification_token`/`password_reset_token`/`workspace_invitation`/
   `shopify_oauth_state`** (Low, audit #20/M1) — unrelated to this pass's scope, not touched.
8. **Dead/inaccurate documentation-as-code and dashboard N+1 patterns beyond the overview card**
   (Medium, audit #14/#18) — `RECONCILIATION_MATCH_STATUSES` was corrected as an unavoidable side
   effect of the C4/H9 rewrite, but the other dashboard sub-endpoints (revenue, orders, payments,
   etc.) were not individually parallelized — only the overview card (H13) was in scope.
9. **`money_at_risk` is computed correctly on the backend but not yet rendered in the frontend** —
   `GET /dashboard/overview` returns the field and `GET /dashboard/money-at-risk` returns the
   breakdown, but `Dashboard.js` was not updated to display either. Discovered during the Phase 6
   final validation pass (2026-08), not part of the original audit; noted here rather than silently
   left inconsistent between the API contract documentation and the actual UI.

---

# Manual Testing Required

None of the following could be exercised in this sandbox (no network egress). All must be run
against a real deployment before production use:

**Shopify**
- [ ] Real OAuth install → callback → token exchange round-trip against a Shopify Partner dev store
- [ ] Real webhook delivery, HMAC verification, and the new per-shop dedup behavior under load
- [ ] The new `order_status_url` consistency check against real order webhook payloads (verify it
      doesn't false-positive-reject legitimate webhooks)
- [ ] Full and incremental sync against a store with a non-trivial number of orders/products/
      customers

**Razorpay**
- [ ] Real credential verification against `POST /razorpay/connect` (valid and invalid credentials)
- [ ] Real webhook delivery to `POST /razorpay/webhooks`, including confirming the O(active
      connections) tenant-resolution scan behaves correctly with more than one connected workspace
- [ ] Real payment/refund/settlement sync and reconciliation against live data
- [ ] Reconnect-after-disconnect flow (verify the new partial unique index actually allows it)

**SMTP / Notifications**
- [ ] Real SMTP delivery of the new `WORKSPACE_NOTIFICATION` template
- [ ] Real webhook delivery to an external receiving endpoint
- [ ] Confirm `notification_delivery_log` entries are created correctly for both success and
      failure cases
- [ ] Trigger a real Shopify sync failure and confirm the `failed_shopify_sync` notification fires

**Exports**
- [ ] Download and open a real CSV, Excel, and PDF export in their respective applications (not
      just byte-count verification, which is all that was possible here)
- [ ] Confirm the 24h TTL expiry actually removes old export files from MongoDB
- [ ] Confirm cross-workspace download attempts correctly 404

**Infrastructure**
- [ ] `pip install -r requirements.txt` succeeds with the newly added `httpx`/`openpyxl`/`reportlab`
- [ ] `db.bootstrap()` runs cleanly against a real MongoDB, including the index drop/recreate calls
      for `razorpay_connection`, `razorpay_webhook_event`, and `shopify_webhook_event`
- [ ] `yarn install && yarn build` succeeds for the frontend, including the two modified files
- [ ] Any existing pytest suite (`tests/test_milestone1_auth_workspace.py` and others) run
      end-to-end against a live backend + MongoDB
- [ ] CORS behavior verified with a real `APP_BASE_URL` and a real cross-origin request

---

# Deployment Requirements

- `MONGO_URL`, `DB_NAME` — required (unchanged)
- `JWT_SECRET`, `ENCRYPTION_KEY` — required (unchanged)
- `APP_BASE_URL` — required for the CORS fix to allow the real frontend origin (previously optional
  in practice because the wildcard fallback masked its absence)
- `CORS_ORIGINS` — recommended to set explicitly in production rather than relying on the
  `APP_BASE_URL` fallback
- `ENVIRONMENT=production` — should be set in production so `/shopify/webhooks/test` stays disabled
- `ENABLE_TEST_ENDPOINTS` — must be left unset/`false` in production
- SMTP settings — required for real email delivery (notifications and auth emails); without them,
  email-dependent flows degrade to `PENDING_NO_TRANSPORT`/logged-only, not a crash
- Razorpay: **no longer a deployment-level credential** — each workspace configures its own via
  `POST /razorpay/connect`; only `ENCRYPTION_KEY` is needed at the deployment level to support it
- `httpx`, `openpyxl`, `reportlab` — now declared in `requirements.txt`; ensure the deployment's
  install step actually picks up the updated file

---

# Verification Performed

- `python3 -m py_compile` on the full backend tree (`find app -name "*.py"` + `server.py`) after
  every edit, clean throughout.
- The three new export writers (CSV via stdlib `csv`, Excel via `openpyxl`, PDF via `reportlab`)
  were smoke-tested standalone in this sandbox with a representative row and confirmed to produce
  real, non-trivial file output (44 / 4886 / 1469 bytes respectively).
- `grep`-based cross-checks confirming every newly-used `AppError` code is registered, every
  referenced Mongo collection constant exists, and every caller of `email_service.send()` is
  unaffected by its changed return type.
- Manual brace/paren-balance checks on both modified frontend files, in the absence of a working
  `yarn build` in this sandbox.
- Manual review of every modified file against the specific `ARCHITECTURE_AUDIT.md` finding it was
  meant to resolve.

# Verification NOT Performed

No live backend process was started. No live MongoDB was reached. No live Shopify, Razorpay, or SMTP
service was contacted. No `yarn build`/`yarn install` was run. No pytest suite was executed. This
sandbox has no network egress, which is the same limitation disclosed in `MILESTONE1_REVIEW.md` and
the original `ARCHITECTURE_AUDIT.md` — repeated here rather than glossed over, per the product's own
"never claim implementation, testing, or verification without evidence" rule.

---

# Final Repository Status

**Code:** Complete for all 7 Critical and all 6 High findings from `ARCHITECTURE_AUDIT.md`, plus two
blocking bugs discovered along the way (unregistered `RAZORPAY-*` error codes, missing
`requirements.txt` entries). Compiles cleanly across the full backend tree.

**Verified:** Statically only — compilation, standalone smoke tests of the export writers, and
manual review. Not verified: any live integration.

**Not done, by design:** Medium/Low findings from the audit, and the god-module restructuring
(Critical #5), both explicitly out of scope for this pass.

**Production readiness:** **Not yet.** Backend and frontend implementation are complete and the
Critical/High security and correctness findings are remediated in the source, but the repository has
never been exercised against a real Shopify store, a real Razorpay account, a real SMTP server, or a
real MongoDB in this environment. Treat this as **implementation-complete, integration-untested** —
the manual testing checklist above is not optional before a real production deployment.
