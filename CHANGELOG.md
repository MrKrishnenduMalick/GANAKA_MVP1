# Changelog

All notable changes to Ganaka are documented in this file. Dates reflect when work was performed in
this project's working sessions, not calendar-time public releases.

## [1.0.0] — 2026-08

### Fixed — Critical
- **Razorpay multi-tenant credential model.** `POST /razorpay/connect` now requires and verifies a
  workspace's own `key_id`/`key_secret`/optional `webhook_secret` against the live Razorpay API,
  encrypted at rest. Previously every workspace shared one deployment-wide credential.
- **Real export file generation.** CSV/Excel/PDF exports now genuinely generate files (`openpyxl`,
  `reportlab`) served by a real, workspace-scoped, TTL'd `GET /exports/download/{filename}`.
  Previously every export returned a fabricated download URL pointing at nothing.
- **Real notification delivery.** Email (SMTP) and webhook (HTTP POST) notifications are now
  actually sent and logged with an honest status. Previously `send_notification` only logged and
  always reported success.
- **Settlement matching correctness improved.** Replaced a workspace-wide "any settlement exists"
  heuristic with a per-payment settlement-window check.
- **Cross-tenant Shopify webhook isolation.** Webhook idempotency dedup is now scoped per shop
  (was a global hash, causing a real cross-tenant data-loss bug); added a payload/header consistency
  check for order-topic webhooks as a partial spoofing mitigation.
- **"Money At Risk" implemented.** A required financial detection rule that had no implementation
  anywhere in the codebase; now computed via `GET /dashboard/money-at-risk` and folded into the
  dashboard overview.
- **Module boundary collapse** — audited and explicitly deferred (not fixed) by scope decision; see
  Known Limitations in `FINAL_RELEASE_REPORT.md`.

### Fixed — High
- **Incremental sync completed.** Moved out of the router (which had business logic embedded
  directly in it) into the service layer; performs a real, idempotent resync; the persisted job
  status always matches the API response.
- **Reconciliation explainability fields added.** Every result and exception now carries
  Evidence/Business Rule/Calculation/Explanation/Recommendation, replacing a single free-text reason
  and one hardcoded suggested action for every exception type.
- **Razorpay webhook receiver added.** `POST /razorpay/webhooks`, previously entirely absent despite
  the database schema being provisioned for it.
- **CORS hardened.** `CORS_ORIGINS="*"` combined with credentialed requests — a live misconfiguration
  — is now refused; falls back to `APP_BASE_URL`, fails closed otherwise.
- **Test-only webhook endpoint gated.** `/shopify/webhooks/test` now returns 404 unless explicitly
  enabled outside production.
- **Dashboard overview parallelized.** 13 sequential database queries now run concurrently.

### Fixed — Other (discovered during remediation, not on the original audit)
- Registered `RAZORPAY-005` through `RAZORPAY-009` and `EXPORT-001` in the error registry — these
  codes were raised throughout the code but never registered, causing every Razorpay error path to
  crash with an unhandled `KeyError` instead of returning a real HTTP response.
- Fixed a `razorpay_connection` unique-index bug that made reconnecting after a disconnect
  impossible.
- Added `httpx`, `openpyxl`, and `reportlab` to `requirements.txt` — all were already imported/used
  by the code (or newly required by the export fix) but missing from the dependency manifest.
- Corrected `backend/.env.example`, which had drifted from what `app/core/config.py` actually reads
  (`SECRET_KEY` → `JWT_SECRET`, `SESSION_MAX_IDLE_MINUTES` → `SESSION_IDLE_TIMEOUT_MINUTES`,
  `LOCKOUT_MINUTES` → `ACCOUNT_LOCK_MINUTES`, removed the nonexistent `SESSION_MAX_ABSOLUTE_DAYS`,
  removed the now-nonexistent global Razorpay credential variables).
- Added `frontend/.env.example` (did not previously exist).

### Changed
- `POST /razorpay/connect` request contract changed to require a credential body (see § API
  Contract Changes in `FIX_SUMMARY.md`) — the one unavoidable breaking change in this release.
- `pages/razorpay/Connect.js` updated with a credential-entry form to match.
- `pages/reports/Export.js` updated to actually download the file the export endpoints now generate.

### Documentation
- Corrected `README.md`, `PROJECT_STATUS.md`, `IMPLEMENTATION_REPORT.md`, `DEPLOYMENT.md`,
  `PRODUCTION_CHECKLIST.md`, `INTEGRATION_GUIDE.md`, `VERIFIED.md` to remove overstated readiness
  claims and stale references to the removed global Razorpay credentials.
- Added `FIX_SUMMARY.md`, `VERSION.md`, `CHANGELOG.md`, `RELEASE_NOTES.md`, `LICENSE_NOTICE.md`,
  `RELEASE_MANIFEST.md`, `RELEASE_CHECKLIST.md` (this release).
- Rewrote `FINAL_RELEASE_REPORT.md` in full to accurately distinguish Implementation Complete /
  Engineering Verified / Requires Real Integration Testing, rather than an unconditional
  "Ready for Production Deployment" claim.

## [0.x] — 2026-06 (unversioned, superseded)

Original implementation of Milestones 1–7: Authentication & Workspace, Shopify Integration,
Razorpay Integration, Financial Reconciliation Engine, Dashboard & Analytics, Production Readiness
features (Exports/Notifications/Health), and the complete frontend application. Declared
"production-ready" at the time; this claim was later found inaccurate by an independent audit (see
1.0.0 above).
