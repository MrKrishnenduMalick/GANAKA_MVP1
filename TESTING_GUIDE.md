# Ganaka — Testing Guide

This guide explains how to run the test suite, what each test covers, and how to interpret results.

---

## Table of Contents

1. [Test Structure](#1-test-structure)
2. [Backend Tests](#2-backend-tests)
3. [Frontend Tests](#3-frontend-tests)
4. [End-to-End Tests](#4-end-to-end-tests)
5. [Manual Testing](#5-manual-testing)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Test Structure

```
tests/
├── __init__.py
├── test_milestone1_auth_workspace.py      # Milestone 1: Authentication & Workspace
├── test_milestone2_shopify_oauth.py       # Milestone 2: Shopify OAuth
├── test_milestone2_shopify_sync.py        # Milestone 2: Shopify Sync
├── test_milestone2_shopify_webhooks.py    # Milestone 2: Shopify Webhooks
├── test_milestone3_razorpay.py            # Milestone 3: Razorpay Integration
├── test_milestone4_reconciliation.py      # Milestone 4: Reconciliation Engine
├── test_milestone5_dashboard.py           # Milestone 5: Dashboard & Analytics
└── test_milestone6_production.py          # Milestone 6: Production Readiness

test_reports/
├── iteration_1.json                        # Frontend e2e test results
└── pytest/                                  # Backend test results
```

---

## 2. Backend Tests

### Prerequisites

- Python 3.11+
- MongoDB 6.0+ running locally or MongoDB Atlas connection
- Backend dependencies installed: `pip install -r backend/requirements.txt`
- Environment variables set in `backend/.env`

### Running All Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Running Specific Test Files

```bash
# Milestone 1: Authentication & Workspace
python -m pytest tests/test_milestone1_auth_workspace.py -v

# Milestone 2: Shopify OAuth
python -m pytest tests/test_milestone2_shopify_oauth.py -v

# Milestone 2: Shopify Sync
python -m pytest tests/test_milestone2_shopify_sync.py -v

# Milestone 2: Shopify Webhooks
python -m pytest tests/test_milestone2_shopify_webhooks.py -v

# Milestone 3: Razorpay
python -m pytest tests/test_milestone3_razorpay.py -v

# Milestone 4: Reconciliation
python -m pytest tests/test_milestone4_reconciliation.py -v

# Milestone 5: Dashboard
python -m pytest tests/test_milestone5_dashboard.py -v

# Milestone 6: Production Readiness
python -m pytest tests/test_milestone6_production.py -v
```

### Running Specific Tests

```bash
# Run a specific test class
python -m pytest tests/test_milestone1_auth_workspace.py::TestAuthWorkspace -v

# Run a specific test method
python -m pytest tests/test_milestone1_auth_workspace.py::TestAuthWorkspace::test_login -v

# Run tests matching a keyword
python -m pytest tests/ -k "reconciliation" -v
```

### Test Configuration

Tests are configured in `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### Test Data

Tests use seeded data created directly in MongoDB. Helper functions in each test file create:
- Verified users with known passwords
- Workspaces with default roles
- Shopify orders, Razorpay payments/refunds/settlements
- Workspace settings with tolerances

### Rate Limits in Tests

Tests are subject to live rate limits:
- Login: 10/min
- Register: 5/hour
- Forgot password: 5/hour

If you hit rate limits, wait 60+ seconds before retrying. Tests include automatic retry logic for 429 responses.

### Known Limitations

1. **Local interpreter lacks dependencies** — `motor`, `pymongo`, `bcrypt`, `pyjwt` may not be installed locally. Tests must run in an environment with these packages.
2. **Shopify/Razorpay/Google credentials** — Tests that require live API credentials are skipped until configured.
3. **Email transport** — No SMTP configured; emails are recorded in `outbound_email` collection. Tests read tokens from there.
4. **Test credentials** — Use `memory/test_credentials.md` for QA accounts.

---

## 3. Frontend Tests

### Prerequisites

- Node.js 18+
- Dependencies installed: `cd frontend && yarn install` or `npm install`

### Running Tests

```bash
cd frontend
yarn test
# or
npm test
```

### Test Coverage

Frontend tests cover:
- Component rendering
- User interactions
- API integration (mocked)
- Permission-aware UI
- Loading/empty/error states

### Known Limitations

1. **node_modules not installed** — Frontend dependencies are not installed in the local environment. Tests must run in an environment with `node_modules`.
2. **E2E tests** — Playwright e2e tests require a running backend and browser automation. See `test_reports/iteration_1.json` for previous results.

---

## 4. End-to-End Tests

### Prerequisites

- Backend running on `http://localhost:8001`
- Frontend running on `http://localhost:3000`
- MongoDB running and populated with test data
- Browser automation tools (Playwright, Cypress, etc.)

### Running E2E Tests

```bash
# Using Playwright
cd frontend
npx playwright test

# Using Cypress
cd frontend
npx cypress open
```

### E2E Test Flows

1. **Authentication Flow**
   - Register → Verify email → Login → Logout
   - Forgot password → Reset password → Login with new password

2. **Workspace Flow**
   - Create workspace → Invite member → Accept invitation → Switch workspace

3. **Shopify Flow**
   - Connect Shopify → Run sync → View orders → View products → View customers

4. **Razorpay Flow**
   - Connect Razorpay → Run sync → View payments → View refunds → View settlements

5. **Reconciliation Flow**
   - Run reconciliation → View results → View exceptions → View summary

6. **Dashboard Flow**
   - View dashboard → Check charts → Apply date filters

7. **Reports Flow**
   - Export reconciliation results → Export exceptions → Export dashboard summary

8. **Settings Flow**
   - Update workspace settings → Manage members → Manage roles → View sessions → Revoke session

### Previous E2E Results

See `test_reports/iteration_1.json` for the first-pass e2e test results:
- 12/13 flows passed on first pass
- 1 HIGH bug fixed (login error message)
- 2 LOW issues fixed (DOM nesting, testid naming)

---

## 5. Manual Testing

### Backend Startup

```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Verify:
- No import errors
- No runtime errors
- Health check responds: `curl http://localhost:8001/api/v1/health`

### Frontend Startup

```bash
cd frontend
yarn start
# or
npm start
```

Verify:
- No compilation errors
- App loads at `http://localhost:3000`
- Login page renders

### API Testing with curl

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Register
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}'

# Get workspaces (replace TOKEN)
curl http://localhost:8001/api/v1/workspaces \
  -H "Authorization: Bearer TOKEN"
```

### Database Verification

```bash
# Connect to MongoDB
mongosh ganaka

# Verify collections
show collections

# Verify indexes
db.user.getIndexes()
db.workspace.getIndexes()
db.shopify_order.getIndexes()
db.razorpay_payment.getIndexes()
db.reconciliation_result.getIndexes()

# Count documents
db.user.countDocuments({})
db.workspace.countDocuments({})
db.shopify_order.countDocuments({})
db.razorpay_payment.countDocuments({})
db.reconciliation_result.countDocuments({})
```

---

## 6. Troubleshooting

### Backend Tests Fail with Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'motor'`

**Solution:** Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### Backend Tests Fail with Connection Errors

**Symptom:** `ServerSelectionTimeoutError: localhost:27017`

**Solution:** Start MongoDB or update `MONGO_URL` in `.env`:
```bash
# Start MongoDB locally
mongod

# Or use MongoDB Atlas
# Update MONGO_URL in backend/.env
```

### Frontend Tests Fail with Module Errors

**Symptom:** `Module not found: Error: Can't resolve '...'`

**Solution:** Install dependencies:
```bash
cd frontend
yarn install
# or
npm install
```

### Rate Limit Errors in Tests

**Symptom:** `429 Too Many Requests`

**Solution:** Wait 60+ seconds before retrying. Tests include automatic retry logic.

### Email Verification Tests Fail

**Symptom:** Cannot find verification token

**Solution:** Read token from `outbound_email` collection:
```bash
mongosh ganaka --quiet --eval \
  'db.outbound_email.find({to_email: "test@example.com", template: "EMAIL_VERIFICATION"}).sort({created_at: -1}).limit(1).pretty()'
```

### Shopify/Razorpay Tests Skipped

**Symptom:** `SKIPPED: Shopify credentials not configured`

**Solution:** Configure credentials in `backend/.env`:
```env
SHOPIFY_API_KEY=...
SHOPIFY_API_SECRET=...
SHOPIFY_APP_URL=...
ENCRYPTION_KEY=...
```

### Frontend Build Fails

**Symptom:** `craco: command not found`

**Solution:** Use npm instead of yarn, or install yarn:
```bash
cd frontend
npm run build
# or
yarn install
yarn build
```

---

## 7. Test Coverage

### Backend Coverage

| Module | Tests | Coverage |
|---|---|---|
| Authentication | 18+ | Register, login, logout, refresh, password reset, sessions, lockout |
| Workspace | 15+ | CRUD, settings, members, invitations, switch, ownership transfer |
| RBAC | 10+ | Roles, permissions, custom roles, plan gates |
| Shopify OAuth | 8+ | Install, callback, status, disconnect, HMAC verification |
| Shopify Sync | 6+ | Initial sync, idempotency, pagination, filters |
| Shopify Webhooks | 8+ | HMAC verification, deduplication, incremental sync |
| Razorpay | 8+ | Connect, disconnect, sync, list, pagination, filters |
| Reconciliation | 6+ | Run, results, exceptions, summary, idempotency |
| Dashboard | 8+ | Overview, revenue, orders, payments, refunds, settlements, exceptions, match rate |
| Production | 6+ | Health, exports, notifications, RBAC |

### Frontend Coverage

| Page | Coverage |
|---|---|
| Landing | Rendering, navigation |
| Login | Form validation, error handling, password visibility |
| Register | Form validation, password checklist |
| Forgot/Reset Password | Form validation, token handling |
| Verify Email | Token validation, success/error states |
| Dashboard | Charts, KPIs, loading/empty states, date filters |
| Shopify Connect | OAuth flow, connection status, disconnect |
| Shopify Sync | Sync trigger, status display |
| Razorpay Connect | Connection status, connect/disconnect |
| Reconciliation Run | Run trigger, loading state |
| Reconciliation Results | Results list, pagination |
| Reconciliation Exceptions | Exceptions list, severity display |
| Reports Export | Format selection, date filters, export buttons |
| Notifications Preferences | Toggle switches, save/load |
| Settings | Workspace, members, roles, sessions |

---

## 8. Continuous Integration

### Recommended CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && python -m pytest tests/ -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm run build
```

---

## 9. Performance Testing

### Load Testing

Use a tool like `locust` or `k6` to simulate load:

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8001
```

### Performance Targets

- Backend response time: < 500ms for typical requests
- Frontend page load: < 3s on 3G
- Database queries: < 100ms (no full collection scans)
- Reconciliation job: < 30s for 1000 orders

---

## 10. Security Testing

### Authentication Tests

- ✅ Unauthenticated requests return 401
- ✅ Invalid tokens return 401
- ✅ Expired tokens return 401
- ✅ Refresh token rotation works
- ✅ Account lockout after 5 failures

### Authorization Tests

- ✅ VIEWER cannot access admin endpoints
- ✅ Cross-workspace access denied
- ✅ Owner-only operations protected
- ✅ RBAC permissions enforced

### Input Validation Tests

- ✅ Invalid email format rejected
- ✅ Weak password rejected
- ✅ SQL injection prevented (MongoDB parameterized queries)
- ✅ XSS prevented (React escapes by default)
- ✅ CSRF protected (SameSite cookies)

### Webhook Security Tests

- ✅ Invalid HMAC rejected
- ✅ Duplicate payloads rejected
- ✅ Replay attacks prevented (timestamp validation)

---

## 11. Test Reports

### Backend Test Reports

Run tests with JSON report:
```bash
cd backend
python -m pytest tests/ -v --json-report --output=test_reports/pytest/report.json
```

### Frontend Test Reports

Run tests with coverage:
```bash
cd frontend
npm test -- --coverage
```

### E2E Test Reports

Playwright generates HTML reports:
```bash
cd frontend
npx playwright test --reporter=html
```

---

## 12. Sign-Off

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] E2E tests pass (or are documented as manual)
- [ ] Performance tests meet targets
- [ ] Security tests pass
- [ ] Test coverage is acceptable (>80%)
- [ ] No flaky tests
- [ ] Test suite runs in CI

**Date:** _______________

**Signed:** _______________