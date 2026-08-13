# Ganaka — Integration Guide

This guide validates the complete application flow from authentication to reports, ensuring every API used by the frontend exists and request/response contracts match.

---

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Workspace Flow](#2-workspace-flow)
3. [Shopify Connection Flow](#3-shopify-connection-flow)
4. [Shopify Sync Flow](#4-shopify-sync-flow)
5. [Razorpay Connection Flow](#5-razorpay-connection-flow)
6. [Razorpay Sync Flow](#6-razorpay-sync-flow)
7. [Reconciliation Flow](#7-reconciliation-flow)
8. [Dashboard Flow](#8-dashboard-flow)
9. [Reports Flow](#9-reports-flow)
10. [Notifications Flow](#10-notifications-flow)
11. [Settings Flow](#11-settings-flow)

---

## 1. Authentication Flow

### Frontend Pages
- `Login.js` — `/login`
- `Register.js` — `/register`
- `ForgotPassword.js` — `/forgot-password`
- `ResetPassword.js` — `/reset-password`
- `VerifyEmail.js` — `/verify-email`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | `POST /api/v1/auth/register` |
| POST | `/api/v1/auth/login` | Public | `POST /api/v1/auth/login` |
| POST | `/api/v1/auth/google` | Public | `POST /api/v1/auth/google` |
| POST | `/api/v1/auth/refresh` | Refresh token | `POST /api/v1/auth/refresh` |
| POST | `/api/v1/auth/logout` | Bearer | `POST /api/v1/auth/logout` |
| POST | `/api/v1/auth/logout-all` | Bearer | `POST /api/v1/auth/logout-all` |
| POST | `/api/v1/auth/forgot-password` | Public | `POST /api/v1/auth/forgot-password` |
| POST | `/api/v1/auth/reset-password` | Public | `POST /api/v1/auth/reset-password` |
| GET | `/api/v1/auth/verify-email` | Public | `GET /api/v1/auth/verify-email` |
| GET | `/api/v1/auth/me` | Bearer | `GET /api/v1/auth/me` |
| GET | `/api/v1/auth/sessions` | Bearer | `GET /api/v1/auth/sessions` |
| DELETE | `/api/v1/auth/sessions/{id}` | Bearer | `DELETE /api/v1/auth/sessions/{id}` |

### Request/Response Contract

**Register:**
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}

// Response (201)
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "status": "EMAIL_PENDING",
  "message": "Registration successful. Please verify your email."
}
```

**Login:**
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

// Response (200)
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "status": "ACTIVE"
  },
  "workspace": {
    "id": "uuid",
    "name": "My Workspace",
    "role": "OWNER",
    "permissions": ["..."]
  }
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/auth/router.py`
- ✅ Frontend calls match documented paths
- ✅ Request/response schemas match `backend/app/modules/auth/schemas.py`
- ✅ Error envelope is consistent (`timestamp`, `status`, `code`, `message`, `path`, `requestId`)

---

## 2. Workspace Flow

### Frontend Pages
- `WorkspaceSettings.js` — `/app/settings/workspace`
- `Members.js` — `/app/settings/members`
- `Roles.js` — `/app/settings/roles`
- `Sessions.js` — `/app/settings/sessions`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| GET | `/api/v1/workspaces` | Bearer | `GET /api/v1/workspaces` |
| POST | `/api/v1/workspaces` | Bearer | `POST /api/v1/workspaces` |
| GET | `/api/v1/workspaces/{id}` | `workspace.read` | `GET /api/v1/workspaces/{id}` |
| PATCH | `/api/v1/workspaces/{id}` | `workspace.update` | `PATCH /api/v1/workspaces/{id}` |
| DELETE | `/api/v1/workspaces/{id}` | Owner | `DELETE /api/v1/workspaces/{id}` |
| GET | `/api/v1/workspaces/{id}/settings` | `workspace.read` | `GET /api/v1/workspaces/{id}/settings` |
| PATCH | `/api/v1/workspaces/{id}/settings` | `workspace.settings` | `PATCH /api/v1/workspaces/{id}/settings` |
| GET | `/api/v1/workspaces/members` | `workspace.read` | `GET /api/v1/workspaces/members` |
| POST | `/api/v1/workspaces/members` | `workspace.members` | `POST /api/v1/workspaces/members` |
| PATCH | `/api/v1/workspaces/members/{id}` | `workspace.members` | `PATCH /api/v1/workspaces/members/{id}` |
| DELETE | `/api/v1/workspaces/members/{id}` | `workspace.members` | `DELETE /api/v1/workspaces/members/{id}` |
| POST | `/api/v1/workspaces/invitations` | `workspace.members` | `POST /api/v1/workspaces/invitations` |
| POST | `/api/v1/workspaces/invitations/accept` | Bearer | `POST /api/v1/workspaces/invitations/accept` |
| POST | `/api/v1/workspaces/{id}/switch` | Bearer | `POST /api/v1/workspaces/{id}/switch` |
| POST | `/api/v1/workspaces/{id}/transfer-ownership` | Owner | `POST /api/v1/workspaces/{id}/transfer-ownership` |

### Validation
- ✅ All endpoints exist in `backend/app/modules/workspace/router.py`
- ✅ Frontend calls match documented paths
- ✅ Request/response schemas match `backend/app/modules/workspace/schemas.py`
- ✅ Workspace isolation is enforced (`workspace_id` from token, never client)

---

## 3. Shopify Connection Flow

### Frontend Pages
- `Connect.js` — `/app/shopify/connect`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/shopify/install` | `shopify.connect` | `POST /api/v1/shopify/install` |
| GET | `/api/v1/shopify/callback` | `shopify.connect` | `GET /api/v1/shopify/callback` |
| GET | `/api/v1/shopify/status` | `shopify.connect` | `GET /api/v1/shopify/status` |
| DELETE | `/api/v1/shopify/disconnect` | `shopify.connect` | `DELETE /api/v1/shopify/disconnect` |

### Request/Response Contract

**Install:**
```json
// Request
{
  "shop_domain": "my-store.myshopify.com"
}

// Response (201)
{
  "install_url": "https://my-store.myshopify.com/admin/oauth/authorize?..."
}
```

**Status:**
```json
// Response (200)
{
  "connected": true,
  "connection": {
    "id": "uuid",
    "workspace_id": "uuid",
    "shop_domain": "my-store.myshopify.com",
    "shop_name": "My Store",
    "scopes": "read_orders,read_products,read_customers",
    "status": "ACTIVE",
    "installed_at": "2024-01-01T00:00:00Z"
  }
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ OAuth flow is HMAC-verified and state-protected
- ✅ Access token is encrypted at rest (AES-256-GCM)

---

## 4. Shopify Sync Flow

### Frontend Pages
- `Sync.js` — `/app/shopify/sync`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/shopify/sync` | `shopify.connect` | `POST /api/v1/shopify/sync` |
| GET | `/api/v1/shopify/sync/status/{job_id}` | `shopify.connect` | `GET /api/v1/shopify/sync/status/{job_id}` |
| GET | `/api/v1/shopify/orders` | `finance.read` | `GET /api/v1/shopify/orders` |
| GET | `/api/v1/shopify/products` | `workspace.read` | `GET /api/v1/shopify/products` |
| GET | `/api/v1/shopify/customers` | `workspace.read` | `GET /api/v1/shopify/customers` |

### Request/Response Contract

**Sync:**
```json
// Request
{
  "resources": ["orders", "products", "customers"]
}

// Response (200)
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "counts": {
    "orders": 100,
    "products": 50,
    "customers": 200
  }
}
```

**List Orders:**
```json
// Response (200)
{
  "items": [
    {
      "id": "uuid",
      "shopify_id": 12345,
      "order_number": 1001,
      "total": 100.00,
      "currency": "INR",
      "financial_status": "paid",
      "payment_gateway_names": ["Razorpay"]
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Sync is idempotent (upsert by `workspace_id` + `shopify_id`)
- ✅ Pagination and filters are implemented

---

## 5. Razorpay Connection Flow

### Frontend Pages
- `Connect.js` — `/app/razorpay/connect`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/razorpay/connect` | `razorpay.connect` | `POST /api/v1/razorpay/connect` |
| GET | `/api/v1/razorpay/status` | `razorpay.connect` | `GET /api/v1/razorpay/status` |
| DELETE | `/api/v1/razorpay/disconnect` | `razorpay.connect` | `DELETE /api/v1/razorpay/disconnect` |
| POST | `/api/v1/razorpay/webhooks` | none (public — verified by per-workspace signature, added 2026-08) | Razorpay calls this directly, not the frontend |

### Request/Response Contract

**Connect:**
```json
// Request — corrected 2026-08: this workspace's OWN Razorpay credentials are
// now required (there is no deployment-wide credential any more — see
// ARCHITECTURE_AUDIT.md #1 / FIX_SUMMARY.md). key_secret and webhook_secret
// are verified against the live Razorpay API, then encrypted at rest and
// never returned.
{
  "key_id": "rzp_live_xxxxxxxxxxxx",
  "key_secret": "your_key_secret",
  "webhook_secret": "your_webhook_secret"  // optional, needed for POST /razorpay/webhooks
}

// Response (201)
{
  "id": "uuid",
  "workspace_id": "uuid",
  "key_id": "rzp_...",
  "account_name": "My Store",
  "status": "ACTIVE",
  "installed_at": "2024-01-01T00:00:00Z"
}
```

**Status:**
```json
// Response (200)
{
  "connected": true,
  "connection": {
    "id": "uuid",
    "key_id": "rzp_...",
    "account_name": "My Store",
    "status": "ACTIVE"
  }
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Key secret is encrypted at rest (AES-256-GCM)
- ✅ Key secret and webhook secret are never returned to client
- ✅ Corrected 2026-08: credentials are per-workspace, not a shared deployment-wide credential (`ARCHITECTURE_AUDIT.md` #1)

---

## 6. Razorpay Sync Flow

### Frontend Pages
- None (sync triggered from Razorpay Connect page)

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/razorpay/sync` | `razorpay.connect` | `POST /api/v1/razorpay/sync` |
| GET | `/api/v1/razorpay/payments` | `finance.read` | `GET /api/v1/razorpay/payments` |
| GET | `/api/v1/razorpay/refunds` | `finance.read` | `GET /api/v1/razorpay/refunds` |
| GET | `/api/v1/razorpay/settlements` | `finance.read` | `GET /api/v1/razorpay/settlements` |

### Request/Response Contract

**Sync:**
```json
// Response (200)
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "counts": {
    "payments": 100,
    "refunds": 5,
    "settlements": 10
  }
}
```

**List Payments:**
```json
// Response (200)
{
  "items": [
    {
      "id": "uuid",
      "razorpay_id": "pay_...",
      "order_id": "order_...",
      "amount": 100.00,
      "currency": "INR",
      "status": "captured",
      "method": "card",
      "captured": true
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Sync is idempotent (upsert by `workspace_id` + `razorpay_id`)
- ✅ Amounts are converted from paise to rupees on import
- ✅ Pagination and filters are implemented

---

## 7. Reconciliation Flow

### Frontend Pages
- `Run.js` — `/app/reconciliation/run`
- `Results.js` — `/app/reconciliation/results`
- `Exceptions.js` — `/app/reconciliation/exceptions`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/reconciliation/run` | `reconciliation.run` | `POST /api/v1/reconciliation/run` |
| GET | `/api/v1/reconciliation/results` | `reconciliation.run` | `GET /api/v1/reconciliation/results` |
| GET | `/api/v1/reconciliation/exceptions` | `reconciliation.run` | `GET /api/v1/reconciliation/exceptions` |
| GET | `/api/v1/reconciliation/summary` | `reconciliation.run` | `GET /api/v1/reconciliation/summary` |

### Request/Response Contract

**Run:**
```json
// Request (query params)
{
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-12-31T23:59:59Z"
}

// Response (200)
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "counts": {
    "total": 100,
    "matched": 80,
    "partial_match": 10,
    "missing_payment": 5,
    "ghost_order": 3,
    "duplicate_payment": 2
  }
}
```

**Results:**
```json
// Response (200)
{
  "items": [
    {
      "id": "uuid",
      "match_status": "MATCHED",
      "shopify_order_id": 12345,
      "amount_shopify": 100.00,
      "amount_razorpay": 100.00,
      "confidence": 0.95,
      "reason": "Exact amount match"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

**Exceptions:**
```json
// Response (200)
{
  "items": [
    {
      "id": "uuid",
      "exception_type": "GHOST_ORDER",
      "severity": "CRITICAL",
      "status": "OPEN",
      "shopify_order_id": 12345,
      "amount": 100.00,
      "root_cause": "No payment found after settlement window",
      "suggested_action": "Review manually"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Reconciliation engine implements discrepancy decision table (Steps 0-5)
- ✅ Results and exceptions are persisted
- ✅ Pagination and filters are implemented

---

## 8. Dashboard Flow

### Frontend Pages
- `Dashboard.js` — `/app/dashboard`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| GET | `/api/v1/dashboard/overview` | `dashboard.read` | `GET /api/v1/dashboard/overview` |
| GET | `/api/v1/dashboard/revenue` | `dashboard.read` | `GET /api/v1/dashboard/revenue` |
| GET | `/api/v1/dashboard/orders` | `dashboard.read` | `GET /api/v1/dashboard/orders` |
| GET | `/api/v1/dashboard/payments` | `dashboard.read` | `GET /api/v1/dashboard/payments` |
| GET | `/api/v1/dashboard/refunds` | `dashboard.read` | `GET /api/v1/dashboard/refunds` |
| GET | `/api/v1/dashboard/settlements` | `dashboard.read` | `GET /api/v1/dashboard/settlements` |
| GET | `/api/v1/dashboard/exceptions` | `dashboard.read` | `GET /api/v1/dashboard/exceptions` |
| GET | `/api/v1/dashboard/match-rate` | `dashboard.read` | `GET /api/v1/dashboard/match-rate` |
| GET | `/api/v1/dashboard/analytics` | `dashboard.read` | `GET /api/v1/dashboard/analytics` |
| GET | `/api/v1/dashboard/money-at-risk` | `dashboard.read` | Added 2026-08 (`ARCHITECTURE_AUDIT.md` #7). `DashboardOverviewResponse` also gained a `money_at_risk` total field on `GET /dashboard/overview`, but **neither field is yet rendered by `Dashboard.js`** — the backend metric exists and is correct, the frontend UI to display it was not added in this pass. Flagged as a real, verified gap, not glossed over. |

### Request/Response Contract

**Overview:**
```json
// Response (200)
{
  "revenue": 100000.00,
  "total_orders": 100,
  "total_payments": 100000.00,
  "total_refunds": 5000.00,
  "total_settlements": 95000.00,
  "reconciliation_match_rate": 0.95,
  "total_exceptions": 10,
  "critical_exceptions": 3,
  "pending_exceptions": 7,
  "connected_integrations": 2
}
```

**Revenue:**
```json
// Response (200)
{
  "total": 100000.00,
  "daily": [
    {"date": "2024-01-01", "total": 1000.00}
  ],
  "weekly": [
    {"week": "2024-01", "total": 7000.00}
  ],
  "monthly": [
    {"month": "2024-01", "total": 30000.00}
  ]
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Aggregation pipelines are used for efficiency
- ✅ Date range filters are supported

---

## 9. Reports Flow

### Frontend Pages
- `Export.js` — `/app/reports/export`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| POST | `/api/v1/exports/reconciliation-results` | `report.export` | `POST /api/v1/exports/reconciliation-results` |
| POST | `/api/v1/exports/exceptions` | `report.export` | `POST /api/v1/exports/exceptions` |
| POST | `/api/v1/exports/dashboard-summary` | `report.export` | `POST /api/v1/exports/dashboard-summary` |
| POST | `/api/v1/exports/payments` | `report.export` | `POST /api/v1/exports/payments` |
| POST | `/api/v1/exports/refunds` | `report.export` | `POST /api/v1/exports/refunds` |
| POST | `/api/v1/exports/settlements` | `report.export` | `POST /api/v1/exports/settlements` |

### Request/Response Contract

**Export:**
```json
// Request
{
  "format": "csv",
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-12-31T23:59:59Z",
  "status": "captured",
  "match_status": "MATCHED"
}

// Response (200)
{
  "download_url": "/api/v1/exports/download/reconciliation_results_uuid.csv",
  "filename": "reconciliation_results_uuid.csv",
  "format": "csv",
  "record_count": 100
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Export filters are implemented
- ✅ File generation is stubbed (returns download URL)

---

## 10. Notifications Flow

### Frontend Pages
- `Preferences.js` — `/app/notifications/preferences`

### API Endpoints

| Method | Path | Permission | Frontend Call |
|---|---|---|---|
| GET | `/api/v1/notifications/preferences` | `workspace.read` | `GET /api/v1/notifications/preferences` |
| PATCH | `/api/v1/notifications/preferences` | `workspace.update` | `PATCH /api/v1/notifications/preferences` |

### Request/Response Contract

**Get Preferences:**
```json
// Response (200)
{
  "id": "uuid",
  "workspace_id": "uuid",
  "critical_reconciliation_failures": true,
  "failed_shopify_sync": true,
  "failed_razorpay_sync": true,
  "oauth_expiration": true,
  "webhook_failures": true,
  "email_enabled": false,
  "webhook_url": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Update Preferences:**
```json
// Request
{
  "critical_reconciliation_failures": false,
  "email_enabled": true
}

// Response (200)
{
  "id": "uuid",
  "workspace_id": "uuid",
  "critical_reconciliation_failures": false,
  "email_enabled": true,
  ...
}
```

### Validation
- ✅ All endpoints exist in `backend/app/modules/shopify/router.py`
- ✅ Frontend calls match documented paths
- ✅ Preferences are stored in `workspace_settings.notification_settings`

---

## 11. Settings Flow

### Frontend Pages
- `WorkspaceSettings.js` — `/app/settings/workspace`
- `Members.js` — `/app/settings/members`
- `Roles.js` — `/app/settings/roles`
- `Sessions.js` — `/app/settings/sessions`

### API Endpoints

All workspace endpoints are covered in Section 2.

### Validation
- ✅ All endpoints exist in `backend/app/modules/workspace/router.py`
- ✅ Frontend calls match documented paths
- ✅ RBAC is enforced on all mutations
- ✅ Workspace isolation is enforced

---

## Summary

### Total API Endpoints Verified: 40+

### Frontend Pages Verified: 15

### Request/Response Contracts: All match

### Known Gaps
1. **Export file generation** — ✅ Corrected 2026-08: CSV/Excel/PDF files are now genuinely generated (`openpyxl`, `reportlab`) and served from a real `GET /exports/download/{filename}`, workspace-scoped with a 24h TTL. Previously returned a placeholder download URL that pointed at nothing — see `ARCHITECTURE_AUDIT.md` #2 / `FIX_SUMMARY.md`.
2. **Notification delivery** — ✅ Corrected 2026-08: real SMTP email and webhook POST delivery now occur, logged with an honest status. Previously a no-op that always reported success — see `ARCHITECTURE_AUDIT.md` #3 / `FIX_SUMMARY.md`. Still requires real SMTP/webhook infrastructure configured in the deployment to actually deliver anything.
3. **Google sign-in** — endpoint exists but requires `GOOGLE_CLIENT_ID` to be configured.
4. **Razorpay** — ✅ Corrected 2026-08: now genuinely multi-tenant (each workspace connects its own account) rather than sharing one deployment-wide credential — see `ARCHITECTURE_AUDIT.md` #1 / `FIX_SUMMARY.md`.

### Integration Status: Implementation Complete — real-world integration testing still required

All frontend pages call the correct backend endpoints, and all request/response contracts match as
of this correction pass. **This has not been verified against a live Shopify store, a live Razorpay
account, a live SMTP server, or a live deployment** — see `FIX_SUMMARY.md` § Manual Testing Required
before treating the application as ready for real-world use.