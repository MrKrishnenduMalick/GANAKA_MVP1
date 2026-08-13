# FILES CHANGED — Post-Audit Remediation Pass

Scope: Critical and High findings from `ARCHITECTURE_AUDIT.md` only (per the fix-only brief). No
Medium/Low findings addressed, no architecture redesign, no module folder split, no database
migration beyond additive/idempotent index changes.

## Backend

### `backend/app/core/config.py`
- Added `_resolve_cors_origins()` (High #11): refuses `CORS_ORIGINS=*` when `allow_credentials=True`
  (always true here); falls back to `APP_BASE_URL`; fails closed otherwise.
- Added `ENVIRONMENT` / `ENABLE_TEST_ENDPOINTS` settings (High #12).
- Removed dependency on global `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/`RAZORPAY_WEBHOOK_SECRET` for
  `razorpay_configured` (Critical #1) — credentials are per-workspace now.

### `backend/server.py`
- CORS middleware now uses `settings.CORS_ORIGINS` instead of a second, divergent inline
  `os.environ.get('CORS_ORIGINS', '*')` read (High #11). Removed unused `import os`.

### `backend/app/core/errors.py`
- Registered `RAZORPAY-005..009` and `EXPORT-001` in `ERROR_REGISTRY`. The Razorpay codes were
  raised throughout `service.py` but never registered — every Razorpay error path crashed with an
  unhandled `KeyError` instead of a real HTTP response. Discovered and fixed as a blocking dependency
  of Critical #1/#8, not itself a numbered audit finding.

### `backend/app/core/db.py`
- Added `EXPORT_FILE`, `NOTIFICATION_DELIVERY_LOG` collections + indexes (Critical #2, #3): TTL on
  `export_file.expires_at`, workspace-scoped list indexes on both.
- `razorpay_connection`: unique index changed from `workspace_id` (all statuses) to a partial unique
  index on `status: ACTIVE` — fixes a pre-existing bug where a workspace could never reconnect
  Razorpay after disconnecting, discovered while implementing Critical #1.
- `razorpay_webhook_event` / `shopify_webhook_event`: dedup unique index changed from a global
  `payload_hash` to `(workspace_id|shop_domain, payload_hash)` (Critical #6, and the equivalent fix
  applied to the new Razorpay webhook path for consistency).

### `backend/app/core/rate_limit.py`
- Added a `razorpay.webhook` bucket so the new webhook receiver can be rate-limited (High #10).

### `backend/app/services/email.py`
- Added a generic `WORKSPACE_NOTIFICATION` template (Critical #3).
- `send()` now returns `{"status", "error"}` instead of `None` — confirmed safe (every existing
  caller uses `await email_service.send(...)` without capturing a return value).

### `backend/app/modules/shopify/schemas.py`
- Added `RazorpayConnectRequest` (Critical #1).
- Added `evidence` / `business_rule` / `calculation` / `explanation` / `recommendation` (all
  optional) to `ReconciliationResultResponse` (High #9).
- Added `money_at_risk` (optional, default 0.0) to `DashboardOverviewResponse`, and new
  `MoneyAtRiskResponse` / `MoneyAtRiskBreakdown` (Critical #7).

### `backend/app/modules/shopify/service.py` (the largest single change)
- **Critical #1**: `connect_razorpay` rewritten to accept and verify per-workspace credentials
  (`_verify_razorpay_credentials`) instead of reading global settings.
- **Critical #2**: added `_write_export_csv` / `_write_export_xlsx` / `_write_export_pdf`,
  `_finalize_export`, `download_export`; every `export_*` function rewritten to actually query,
  generate, and persist a real file instead of returning a fabricated URL.
- **Critical #3**: `send_notification()` rewritten to actually deliver via `email_service.send()`
  and `httpx.post()`, log every attempt, and return an honest status. Wired into `run_sync` and
  `run_incremental_sync`'s FAILED branches.
- **Critical #4**: added `_settled_within_window()`; `_match_status_for_order` rewritten to use it
  instead of a workspace-wide settlement-existence flag.
- **Critical #6**: `process_webhook_event` dedup scoped by `(shop_domain, payload_hash)`; added
  `_payload_shop_domain_consistent()` cross-check for order-topic webhooks.
- **Critical #7**: added `get_money_at_risk()`, `_sum_field()` helper.
- **High #8**: added `run_incremental_sync()` (moved from the router); it now performs a real,
  idempotent resync and the persisted job document always matches the API response.
- **High #9**: `_match_status_for_order` rewritten to return a full explainable dict (`evidence`,
  `business_rule`, `calculation`, `explanation`, `recommendation`) via `_BUSINESS_RULES` /
  `_RECOMMENDATIONS` lookup tables; `run_reconciliation` persists the new fields; exceptions get a
  rule-specific `suggested_action`.
- **High #10**: added `_verify_razorpay_webhook_hmac`, `_resolve_razorpay_workspace`,
  `_active_razorpay_connections`, `_process_razorpay_webhook_payload`,
  `process_razorpay_webhook_event`.
- **High #13**: `get_dashboard_overview` rewritten to issue its independent queries via
  `asyncio.gather` instead of sequential `await`s.
- Added imports: `asyncio`, `csv`, `io`, `json` (module-level, was previously a local import),
  `bson.Binary`, `app.services.email as email_service`.
- `RECONCILIATION_MATCH_STATUSES` corrected to match what the matcher actually returns
  (`GHOST_ORDER` added, unreachable `UNMATCHED`/`MISSING_ORDER` removed) — a side effect of the
  Critical #4/#9 rewrite, not separately scoped work.

### `backend/app/modules/shopify/router.py`
- `/shopify/webhooks/test` gated behind `ENABLE_TEST_ENDPOINTS`/`ENVIRONMENT` (High #12).
- `/shopify/sync/incremental` reduced to input validation + delegation to
  `service.run_incremental_sync()`; all the direct-DB-write business logic that previously lived
  here was removed (High #8).
- `/razorpay/connect` now takes a `RazorpayConnectRequest` body (Critical #1).
- Added `POST /razorpay/webhooks` (High #10), `GET /exports/download/{filename}` (Critical #2),
  `GET /dashboard/money-at-risk` (Critical #7).
- Import additions: `HTTPException`, `Response`, `settings`, `RazorpayConnectRequest`,
  `MoneyAtRiskResponse`.

### `backend/requirements.txt`
- Added `httpx` (already imported/used by `service.py` for Shopify/Razorpay API calls, but missing
  from this file — a pre-existing gap discovered while verifying builds), `openpyxl` (Critical #2,
  Excel export), `reportlab` (Critical #2, PDF export).

## Frontend

### `frontend/src/pages/razorpay/Connect.js`
- Replaced the single no-input "Connect" button with a form collecting `key_id`/`key_secret`/
  optional `webhook_secret`, required because the backend contract in Critical #1 necessarily
  changed (there was no way to fix "everyone shares one account" without asking each tenant for
  their own credentials).

### `frontend/src/pages/reports/Export.js`
- `onSuccess` now actually fetches the generated file (`GET /exports/download/{filename}`, blob
  response) and triggers a real browser download, instead of only showing a toast naming a file that
  previously never existed anywhere (Critical #2).

## Not modified

Every Medium/Low finding in `ARCHITECTURE_AUDIT.md`, and the module-boundary/god-module issue
(Critical #5), were left untouched per the explicit scope of this pass. See `FIX_SUMMARY.md` §
Remaining Accepted Risks.

## Verification

- `python3 -m py_compile` on the full backend tree (`find app -name "*.py"` + `server.py`), clean
  after every edit.
- The three new export writers (CSV/openpyxl/reportlab) were smoke-tested standalone in this sandbox
  and confirmed to produce real, non-trivial file bytes (44 / 4886 / 1469 bytes for a 1-row sample).
- Manual brace/paren-balance checks on both modified frontend files, in the absence of a working
  `yarn build` (no `node_modules`, no network access to install them in this sandbox).
- Could not run the backend as a live process, could not reach a real MongoDB to verify the new/
  changed indexes apply cleanly, could not run any pytest suite, could not run `yarn build`. These
  gaps are the same class of sandbox limitation disclosed in `MILESTONE1_REVIEW.md` and the original
  `ARCHITECTURE_AUDIT.md`.
