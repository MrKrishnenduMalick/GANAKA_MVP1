# Release Checklist — Ganaka MVP v1.0.0

Status legend: ✅ Done and verified in this release · ⚠️ Partially done / conditional · ⏳ Pending,
requires a real environment this sandbox could not provide.

## Repository Clean
✅ **Done.** `__pycache__`, `.pytest_cache`, `.pyc` files removed. No `.DS_Store`, `Thumbs.db`,
`.idea/`, `.vscode/`, editor swap/backup files found in the source tree (checked in Phase 6/prior
sessions). No `node_modules/`, `.git/`, or `.venv/` present to begin with. Internal tooling
scaffolding (`.emergent/`) and transient test-run output (`test_reports/`) excluded from the release
archive, not from the working repository.

## No Secrets
✅ **Done.** `backend/.env` and `frontend/.env` (both containing real, environment-specific values —
not secrets requiring rotation, but real config) are excluded from the release archive; only
`.env.example` files are included. `git secrets`-style scanning for hardcoded API keys/passwords in
source was not re-run in this pass (was checked in the original `ARCHITECTURE_AUDIT.md` — no
hardcoded secrets found there; not re-verified in Phase 6 beyond confirming `.env` exclusion).

## Documentation Complete
✅ **Done.** All 13 documents required by this release's brief exist: `README.md`,
`ARCHITECTURE_AUDIT.md`, `IMPLEMENTATION_REPORT.md`, `PROJECT_STATUS.md`, `FILES_CHANGED.md`,
`VERIFIED.md`, `FIX_SUMMARY.md`, `FINAL_RELEASE_REPORT.md`, `DEPLOYMENT.md`,
`PRODUCTION_CHECKLIST.md`, `INTEGRATION_GUIDE.md`, `TESTING_GUIDE.md`, `backend/.env.example` (plus
`frontend/.env.example`, added this release). This release additionally adds `CHANGELOG.md`,
`VERSION.md`, `RELEASE_NOTES.md`, `LICENSE_NOTICE.md`, `RELEASE_MANIFEST.md`, and this checklist.
Cross-document consistency verified in Phase 6 (env vars, route counts, Razorpay contract
references, export/notification status claims).

## Backend Compile
✅ **Done.** `python3 -m py_compile` clean across the full backend tree (`app/` + `server.py`),
re-verified in Phase 6. No broken local imports (verified via AST analysis of every `from app...`
import). All 10 sub-routers confirmed mounted in `server.py`. Zero duplicate routes, zero duplicate
named MongoDB indexes, zero orphaned collections (all verified programmatically in Phase 6).

## Frontend Build Required
⏳ **Pending — requires a real environment.** No `node_modules` and no network access existed in the
sandbox this release was prepared in, so `yarn install && yarn build` has never been run against
this codebase. The two files modified in the remediation pass (`pages/razorpay/Connect.js`,
`pages/reports/Export.js`) were manually reviewed and brace/paren-balance checked, which is not a
substitute for a real build. **This must be run before any deployment.**

## Environment Variables Ready
✅ **Done, as documentation.** `backend/.env.example` corrected to match `app/core/config.py`
exactly (verified programmatically in Phase 6 — zero vars used by the code are undocumented, zero
documented vars are unused). `frontend/.env.example` added and verified against actual
`process.env.*` usage in the frontend source. ⏳ **Actual production values** (real MongoDB URI, real
JWT secret, real SMTP credentials, real Shopify Partner app credentials) still need to be
provisioned by whoever deploys this — this repository intentionally ships no real secrets.

## Deployment Guides Ready
✅ **Done.** `DEPLOYMENT.md` corrected in this release to remove references to the now-removed
global Razorpay environment variables. Covers Render (backend) + Vercel (frontend) as the target
platforms.

## Testing Guide Ready
✅ **Done, as documentation.** `TESTING_GUIDE.md` exists and was reviewed for stale references in
this pass (none found beyond what was already corrected). ⏳ **The test suite itself has not been
executed** in this sandbox (no network access to install dependencies or reach a live MongoDB) — see
Manual Testing Pending below.

## Integration Guide Ready
✅ **Done.** `INTEGRATION_GUIDE.md` corrected in this release: the Razorpay connect request/response
example updated to match the real per-workspace credential contract, the new
`POST /razorpay/webhooks` and `GET /dashboard/money-at-risk` endpoints added to their respective
tables, and the "Known Gaps" section corrected to reflect that Exports and Notifications are real
now rather than placeholders. All frontend↔backend endpoint mappings re-verified against the actual
route list in Phase 6.

## Manual Testing Pending
⏳ **Pending — the largest remaining gap before production use.** Nothing in this release has been
exercised against a live Shopify store, a live Razorpay account, a live SMTP server, or a live
MongoDB. Full checklist in `FIX_SUMMARY.md` § Manual Testing Required and
`RELEASE_MANIFEST.md` § Manual Testing Required. This is not a formality — it is the primary
condition that must be satisfied before § Production Deployment Pending below can be checked off.

## Production Deployment Pending
⏳ **Pending.** Do not deploy to production until: (1) Frontend Build Required is resolved, (2) real
environment variables are provisioned, (3) Manual Testing Pending is fully executed against a
staging environment, and (4) the results of that testing are reviewed. See
`FINAL_RELEASE_REPORT.md` § Final Recommendation for the complete, explicit statement of what is and
is not verified as of this release.
