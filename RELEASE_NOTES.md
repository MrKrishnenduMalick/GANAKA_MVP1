# Release Notes — Ganaka MVP v1.0.0

**Release date:** 2026-08
**Audience:** engineering handoff, staging deployment, real-world integration testing

---

## What's in this release

Ganaka v1.0.0 is the first frozen, versioned release of the financial reconciliation MVP for
Shopify-based D2C businesses. It packages Milestones 1–7 (Authentication & Workspace, Shopify
Integration, Razorpay Integration, Financial Reconciliation Engine, Dashboard & Analytics,
Production Readiness, and the complete frontend application) together with the fixes from an
independent architecture and security audit.

## Highlights

- **Razorpay is now genuinely multi-tenant.** Each workspace connects its own Razorpay account with
  its own credentials, verified live and encrypted at rest. Previously every workspace shared one
  platform-wide credential — a real confidentiality defect, now closed.
- **Exports actually work.** CSV, Excel, and PDF exports generate real files you can download.
  Previously the download link pointed at nothing.
- **Notifications actually send.** Email and webhook notifications are delivered for real, with an
  honest delivery log — previously the system always claimed success without sending anything.
- **Money At Risk is implemented.** One of the product's seven core financial detection rules,
  previously entirely missing, now surfaces the total value tied up in unresolved reconciliation
  exceptions.
- **Security hardening.** CORS no longer allows a wildcard origin with credentialed requests; a
  test-only webhook endpoint is no longer reachable in production; Shopify webhook deduplication no
  longer risks silently dropping a different tenant's event.

Full detail on every fix, with file-by-file reasoning, is in `FIX_SUMMARY.md`. The audit that found
these issues is preserved in `ARCHITECTURE_AUDIT.md`.

## Breaking Changes

- `POST /razorpay/connect` now requires a JSON body (`key_id`, `key_secret`, optional
  `webhook_secret`) where it previously took none. This was structurally unavoidable — the entire
  defect being fixed was that the endpoint took no tenant-specific input. The frontend Razorpay
  Connect page has been updated to match.

No other API contract changed in a breaking way. Two response schemas gained additive, optional
fields (`DashboardOverviewResponse.money_at_risk`, five new fields on
`ReconciliationResultResponse`) — existing clients are unaffected.

## What This Release Does NOT Include

- Any fix to Medium or Low severity findings from `ARCHITECTURE_AUDIT.md` — explicitly out of scope
  for this remediation pass.
- A restructuring of the backend module layout. `modules/shopify` still contains Shopify, Razorpay,
  Reconciliation, Dashboard, Exports, Notifications, and Health in one package — a known,
  documented, deliberately-deferred architectural risk.
- A UI for the new `money_at_risk` metric — the backend computes it correctly, but no dashboard card
  was added to display it in this pass.
- Any live verification against a real Shopify store, Razorpay account, SMTP server, or MongoDB
  instance — every fix in this release was verified statically (compilation, standalone smoke
  tests, manual review) in a sandboxed environment with no network access.

## Who Should Read What

- **Deploying to staging?** Start with `DEPLOYMENT.md` and `backend/.env.example` /
  `frontend/.env.example` (both corrected in this release to match the actual code).
- **Running QA before go-live?** Start with `FIX_SUMMARY.md` § Manual Testing Required and
  `TESTING_GUIDE.md`.
- **Reviewing what changed and why?** Start with `FIX_SUMMARY.md`, then `ARCHITECTURE_AUDIT.md` for
  the original findings, then `FILES_CHANGED.md` for the literal diff-level detail.
- **Assessing production readiness?** Start with `FINAL_RELEASE_REPORT.md` § Final Recommendation —
  it deliberately distinguishes Implementation Complete, Engineering Verified, and Requires Real
  Integration Testing rather than giving a single readiness verdict.

## Known Limitations

See `FINAL_RELEASE_REPORT.md` § Known Limitations for the complete list. In brief: settlement
matching is an improved heuristic, not a fully precise match (would require Razorpay's Settlement
Recon API); Shopify webhook spoofing mitigation is partial for payload topics without an embedded
domain field; the `shopify_connection` collection has the same reconnect-after-disconnect bug that
was found and fixed for `razorpay_connection`, but was left unfixed as out of scope; and several
Medium/Low findings from the original audit remain open by design.

## Upgrade Notes

This is the first tagged version — there is no prior version to upgrade from. If deploying over an
existing 2026-06 (pre-audit) instance of this codebase: the MongoDB index changes in this release
are additive/idempotent and safe to apply via the existing `db.bootstrap()` mechanism, but any
workspace that had already connected Razorpay under the old shared-credential model will need to
reconnect with its own credentials after this upgrade, since the stored connection record's shape
and meaning has changed.
