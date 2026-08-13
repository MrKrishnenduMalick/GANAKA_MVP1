# Ganaka — Production Checklist

Use this checklist before deploying to production. Every item must be verified.

---

## Pre-Deployment

### Code Quality
- [ ] All tests pass (`python -m pytest tests/ -v`)
- [ ] Backend compiles without errors (`python -m py_compile server.py`)
- [ ] Frontend builds without errors (`yarn build` or `npm run build`)
- [ ] No hardcoded secrets in code
- [ ] No debug logging in production code
- [ ] No placeholder/mock implementations remain

### Environment Variables
- [ ] `SECRET_KEY` is set (32+ random bytes, never committed)
- [ ] `ENCRYPTION_KEY` is set (32 bytes base64-encoded, never committed)
- [ ] `MONGO_URL` points to production MongoDB (with authentication)
- [ ] `DB_NAME` is set to production database name
- [ ] `CORS_ORIGINS` is set to production domain only (not `*`)
- [ ] `APP_BASE_URL` is set to production URL
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` are set
- [ ] Optional: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `SHOPIFY_APP_URL` are set
- [ ] `ENCRYPTION_KEY` is set (required for Razorpay to be usable — as of 2026-08 each workspace connects its own account via the app UI, there is no deployment-level `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` to set)
- [ ] Optional: `GOOGLE_CLIENT_ID` is set
- [ ] `ENVIRONMENT="production"` is set and `ENABLE_TEST_ENDPOINTS` is unset/`false` (added 2026-08 — keeps the test webhook replay endpoint disabled)

### Security
- [ ] HTTPS is enabled on backend
- [ ] HTTPS is enabled on frontend
- [ ] MongoDB requires authentication
- [ ] MongoDB network access is restricted (not `0.0.0.0/0` in production)
- [ ] Rate limiting is active
- [ ] Audit logging is active
- [ ] Webhook HMAC verification is enabled
- [ ] JWT tokens are signed with strong secret
- [ ] Refresh tokens are httpOnly, Secure, SameSite=Strict
- [ ] Password policy is enforced (12+ chars, complexity, deny-list)
- [ ] Account lockout is enabled (5 failures → 15min lock)

### Database
- [ ] MongoDB Atlas cluster is provisioned
- [ ] Database user is created with least-privilege permissions
- [ ] Database indexes are created (run `bootstrap()` on startup)
- [ ] Backup schedule is configured (daily snapshots)
- [ ] Connection pooling is configured
- [ ] Database name is not `test_database`

### Third-Party Services
- [ ] Shopify Partner app is configured
- [ ] Shopify OAuth redirect URI is registered
- [ ] Shopify webhook URLs are registered
- [ ] Razorpay account is active
- [ ] Razorpay API keys are generated
- [ ] SMTP provider is configured
- [ ] Google OAuth is configured (if using Google sign-in)

---

## Deployment

### Backend (Render)
- [ ] Web Service is created
- [ ] Build command is correct (`pip install -r requirements.txt`)
- [ ] Start command is correct (`uvicorn server:app --host 0.0.0.0 --port $PORT`)
- [ ] Health check path is set (`/api/v1/health`)
- [ ] Environment variables are set in Render dashboard
- [ ] Custom domain is configured (if using)
- [ ] HTTPS is enabled
- [ ] Auto-deploy is enabled (or manual deploy is triggered)

### Frontend (Vercel)
- [ ] Project is imported from repository
- [ ] Root directory is set to `frontend/`
- [ ] Build command is correct (`yarn build` or `npm run build`)
- [ ] Output directory is set to `build/`
- [ ] `REACT_APP_BACKEND_URL` is set to backend URL
- [ ] Custom domain is configured (if using)
- [ ] HTTPS is enabled
- [ ] Deploy is triggered

### DNS
- [ ] Backend domain (`api.your-domain.com`) points to Render
- [ ] Frontend domain (`app.your-domain.com`) points to Vercel
- [ ] DNS propagation is complete (check with `dig` or `nslookup`)
- [ ] SSL certificates are provisioned

---

## Post-Deployment Verification

### Health Checks
- [ ] `GET /api/v1/health` returns 200
- [ ] `GET /api/v1/health/database` returns 200
- [ ] `GET /api/v1/health/shopify` returns 200
- [ ] `GET /api/v1/health/razorpay` returns 200
- [ ] `GET /api/v1/health/reconciliation` returns 200

### Authentication
- [ ] User can register
- [ ] User receives verification email
- [ ] User can login
- [ ] User can logout
- [ ] Refresh token rotation works
- [ ] Account lockout works after 5 failed logins
- [ ] Password reset works

### Workspace
- [ ] User can create workspace
- [ ] User can invite members
- [ ] User can switch workspaces
- [ ] Workspace isolation is enforced (cross-workspace access denied)

### Shopify
- [ ] User can connect Shopify store
- [ ] User can run initial sync
- [ ] User can view orders/products/customers
- [ ] Webhook endpoint accepts HMAC-verified payloads

### Razorpay
- [ ] User can connect Razorpay account
- [ ] User can run sync
- [ ] User can view payments/refunds/settlements

### Reconciliation
- [ ] User can run reconciliation
- [ ] Reconciliation results are generated
- [ ] Reconciliation exceptions are generated
- [ ] Reconciliation summary is accurate

### Dashboard
- [ ] Dashboard loads without errors
- [ ] Revenue chart displays
- [ ] Orders chart displays
- [ ] Payments chart displays
- [ ] Match rate chart displays
- [ ] Date range filters work

### Reports
- [ ] User can export reconciliation results
- [ ] User can export exceptions
- [ ] User can export dashboard summary
- [ ] User can export payments/refunds/settlements

### Notifications
- [ ] User can view notification preferences
- [ ] User can update notification preferences

### Settings
- [ ] User can update workspace settings
- [ ] User can manage members
- [ ] User can manage roles
- [ ] User can view active sessions
- [ ] User can revoke sessions

---

## Monitoring

### Application Logs
- [ ] Backend logs are accessible (Render logs)
- [ ] Frontend logs are accessible (Vercel logs)
- [ ] Log aggregation is configured (optional)
- [ ] Error tracking is configured (optional, e.g., Sentry)

### Database
- [ ] MongoDB Atlas metrics are monitored
- [ ] Slow query alerts are configured
- [ ] Connection count is monitored

### Alerts
- [ ] High CPU/memory alerts are configured
- [ ] High error rate alerts are configured
- [ ] Health check failure alerts are configured
- [ ] Rate limit hit alerts are configured (optional)

---

## Backup & Recovery

- [ ] MongoDB Atlas automated backups are enabled
- [ ] Backup retention period is set (recommended: 7 days)
- [ ] Backup restoration procedure is documented
- [ ] RTO and RPO are defined
- [ ] Backup restoration is tested (at least once)

---

## Compliance

- [ ] Privacy policy is published
- [ ] Terms of service are published
- [ ] Data retention policy is defined
- [ ] GDPR compliance is verified (if serving EU customers)
- [ ] Audit log retention is configured (recommended: 7 years for financial data)
- [ ] Data export mechanism is implemented (for `customers/data_request` webhook)

---

## Performance

- [ ] Backend response time is < 500ms for typical requests
- [ ] Frontend page load time is < 3s on 3G
- [ ] Database queries are optimized (no full collection scans)
- [ ] Pagination is enforced on all list endpoints
- [ ] Static assets are cached (CDN for frontend)
- [ ] Gzip/brotli compression is enabled

---

## Security Final Check

- [ ] No secrets in code or logs
- [ ] No sensitive data in error responses
- [ ] All endpoints require authentication (except public ones)
- [ ] All mutations require authorization (RBAC)
- [ ] All requests are validated (Pydantic schemas)
- [ ] All mutations are audited
- [ ] Webhook HMAC verification is enforced
- [ ] Rate limiting is active
- [ ] CORS is configured correctly
- [ ] Security headers are set (CSP, X-Frame-Options, etc.)

---

## Sign-Off

- [ ] Engineering lead has reviewed this checklist
- [ ] All items are verified
- [ ] Deployment is approved

**Date:** _______________

**Signed:** _______________