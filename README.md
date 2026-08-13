# Ganaka — Financial Reconciliation Platform

Financial reconciliation MVP for Shopify-based D2C businesses. Imports Shopify orders and Razorpay payments/refunds/settlements, reconciles transactions via deterministic business rules, and presents auditable financial evidence. Backend and frontend implementation are complete; see [FIX_SUMMARY.md](./FIX_SUMMARY.md) for current status — real-world integration testing (Shopify, Razorpay, SMTP, live deployment) is still required before production use.

## Technology Stack

- **Backend:** FastAPI 0.110 (Python 3.11) + MongoDB (motor 3.3) + Pydantic v2
- **Frontend:** React 19 (CRA + CRACO, JavaScript) + Tailwind CSS 3.4 + shadcn/ui
- **Authentication:** Custom JWT (pyjwt HS256 + bcrypt) + httpOnly refresh cookies
- **Testing:** pytest 8 + integration tests

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 6.0+
- yarn 1.22+

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure environment variables
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend Setup

```bash
cd frontend
yarn install
yarn start
```

## Required Environment Variables

### Core (Required)
- `MONGO_URL` — MongoDB connection string
- `DB_NAME` — MongoDB database name
- `CORS_ORIGINS` — Comma-separated allowed origins
- `SECRET_KEY` — JWT signing secret (32+ bytes)

### Authentication
- `ACCESS_TOKEN_TTL_MINUTES` — Default: 15
- `REFRESH_TOKEN_TTL_DAYS` — Default: 30
- `SESSION_MAX_IDLE_MINUTES` — Default: 30
- `SESSION_MAX_ABSOLUTE_DAYS` — Default: 30
- `MAX_FAILED_LOGINS` — Default: 5
- `LOCKOUT_MINUTES` — Default: 15

### Email (SMTP)
- `SMTP_HOST` — SMTP server host
- `SMTP_PORT` — SMTP server port (587 for TLS)
- `SMTP_USER` — SMTP username
- `SMTP_PASSWORD` — SMTP password
- `SMTP_FROM` — From email address
- `SMTP_USE_TLS` — Default: true

### Google OAuth (Optional)
- `GOOGLE_CLIENT_ID` — Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` — Google OAuth client secret

### Shopify (Optional)
- `SHOPIFY_API_KEY` — Shopify app client ID
- `SHOPIFY_API_SECRET` — Shopify app client secret
- `SHOPIFY_SCOPES` — OAuth scopes (e.g., `read_orders,read_products,read_customers`)
- `SHOPIFY_APP_URL` — Public base URL for OAuth redirect
- `ENCRYPTION_KEY` — AES-256 key (32 bytes, base64-encoded) for credential encryption
- `SHOPIFY_OAUTH_STATE_TTL_MINUTES` — Default: 15

### Razorpay (Optional)
> **Corrected 2026-08:** Razorpay is per-workspace now, not deployment-wide (see
> `ARCHITECTURE_AUDIT.md` #1 / `FIX_SUMMARY.md`). There is no longer a global `RAZORPAY_KEY_ID` /
> `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` environment variable — each workspace supplies
> and verifies its own credentials via `POST /razorpay/connect`, encrypted at rest.
- `ENCRYPTION_KEY` — same AES-256 key used above; required for Razorpay to be usable at all
  (`settings.razorpay_configured`), since it's what encrypts each workspace's stored credentials

## Production Deployment Checklist

### Security
- [ ] Set strong `SECRET_KEY` (32+ random bytes)
- [ ] Configure `ENCRYPTION_KEY` (32 bytes, base64-encoded)
- [ ] Enable HTTPS (TLS termination at load balancer)
- [ ] Set `CORS_ORIGINS` to production domain only (as of 2026-08 the API also fails closed rather
      than falling back to a wildcard if this is left unset — see `FIX_SUMMARY.md`)
- [ ] Set `ENVIRONMENT=production` and leave `ENABLE_TEST_ENDPOINTS` unset (added 2026-08, keeps
      `/shopify/webhooks/test` disabled)
- [ ] Configure SMTP credentials for email delivery
- [ ] Set up Google OAuth credentials (if using Google sign-in)
- [ ] Set up Shopify Partner credentials (if using Shopify integration)
- [ ] Razorpay credentials are configured **per workspace** via the app UI, not as a deployment
      environment variable (see note above)
- [ ] Enable database authentication (MongoDB)
- [ ] Restrict MongoDB access to application servers only
- [ ] Use environment variables or secrets manager (never commit secrets)

### Performance
- [ ] Enable MongoDB replica set for read scaling
- [ ] Configure MongoDB connection pool size
- [ ] Set up Redis for distributed rate limiting (optional, for multi-instance)
- [ ] Configure uvicorn workers (recommended: 2-4 per CPU core)
- [ ] Set up CDN for frontend assets
- [ ] Enable gzip/brotli compression

### Monitoring
- [ ] Set up application logging (structured JSON logs)
- [ ] Configure log aggregation (e.g., ELK, Datadog, CloudWatch)
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Monitor database performance (slow queries, connections)
- [ ] Set up health check monitoring (`/health`, `/health/database`)
- [ ] Configure alerts for critical errors
- [ ] Monitor rate limit hits

### Backup & Recovery
- [ ] Set up automated MongoDB backups (daily)
- [ ] Test backup restoration procedure
- [ ] Document recovery time objective (RTO) and recovery point objective (RPO)
- [ ] Set up database replication (minimum: 1 secondary)

### Compliance
- [ ] Review data retention policies
- [ ] Enable audit log retention (recommended: 7 years for financial data)
- [ ] Configure GDPR compliance (if serving EU customers)
- [ ] Set up data export mechanism for `customers/data_request` webhook
- [ ] Document incident response procedure

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

## Testing

```bash
# Backend integration tests
cd backend
python -m pytest tests/ -v

# Frontend tests
cd frontend
yarn test
```

## Project Structure

```
backend/
├── app/
│   ├── core/           # Shared utilities (config, db, security, errors, rate limiting)
│   ├── modules/        # Feature modules (auth, workspace, rbac, shopify)
│   └── services/       # External services (email)
├── tests/              # Integration tests
└── server.py           # FastAPI app factory

frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Route pages
│   ├── context/        # React contexts (auth)
│   └── lib/            # Utilities (api client)
└── public/             # Static assets
```

## Milestones

- ✅ Milestone 1: Authentication & Workspace
- ✅ Milestone 2: Shopify Integration
- ✅ Milestone 3: Razorpay Integration (corrected 2026-08 — see `FIX_SUMMARY.md`; was previously a single shared credential across all tenants)
- ✅ Milestone 4: Financial Reconciliation Engine (settlement matching and Money At Risk improved 2026-08 — see `FIX_SUMMARY.md`)
- ✅ Milestone 5: Dashboard & Analytics API
- ✅ Milestone 6: Production Readiness (Exports and Notifications corrected 2026-08 — see `FIX_SUMMARY.md`; were previously non-functional placeholders)
- ✅ Milestone 7: Complete Frontend Application

All milestones are code-complete; see [FIX_SUMMARY.md](./FIX_SUMMARY.md) for what has and has not
been verified against a live environment before treating this as production-ready.

## License

Proprietary — All rights reserved.

## Additional Documentation

- **[ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md)** — Independent architecture/security audit and fix status
- **[FIX_SUMMARY.md](./FIX_SUMMARY.md)** — What was fixed, what remains, what to test before production
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Complete deployment guide for Render (backend) and Vercel (frontend)
- **[PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md)** — Pre/post-deployment checklist
- **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** — API contract validation and integration flows
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** — Test execution guide and troubleshooting
- **[VERIFIED.md](./VERIFIED.md)** — Engineering verification report (2026-06; see `FIX_SUMMARY.md` for corrections)
- **[FINAL_RELEASE_REPORT.md](./FINAL_RELEASE_REPORT.md)** — Final release report (corrected 2026-08)

## Support

For issues and questions, contact the Ganaka team.
</content>
<task_progress>
- [x] Read existing router patterns
- [x] Add export schemas
- [x] Add export service
- [x] Add export router endpoints
- [x] Add notification service
- [x] Add health check endpoints
- [x] Add tests
- [x] FILES_CHANGED.md
- [x] PROJECT_STATUS.md
- [x] NEXT_MILESTONE.md
- [x] IMPLEMENTATION_REPORT.md
- [ ] README.md
- [ ] Final py_compile
</task_progress>
