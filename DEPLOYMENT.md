# Ganaka — Deployment Guide

This guide covers deploying Ganaka to production using Render (backend) and Vercel (frontend), with MongoDB Atlas.

---

## Prerequisites

- MongoDB Atlas cluster (or self-hosted MongoDB 6.0+)
- Domain name with DNS access
- Accounts: Render, Vercel, MongoDB Atlas, Shopify Partner, Razorpay Dashboard

---

## 1. MongoDB Atlas Setup

1. Create a new project and cluster (M0 free tier is sufficient for MVP).
2. In **Database Access**, create a database user with read/write permissions.
3. In **Network Access**, add your deployment IPs or `0.0.0.0/0` for testing.
4. Get the connection string: `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/ganaka?retryWrites=true&w=majority`
5. Enable authentication and TLS (Atlas does this by default).

---

## 2. Backend Deployment (Render)

### Option A: Render Web Service

1. Connect your repository to Render.
2. Create a new **Web Service**:
   - **Runtime:** Docker
   - **Dockerfile path:** `backend/Dockerfile`
   - **Plan:** Starter (or higher for production)
3. Set environment variables (see `backend/.env.example`).
4. Set **Health Check Path:** `/api/v1/health`
5. Deploy.

### Option B: Render without Docker

1. Create a new **Web Service**:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
2. Set environment variables.
3. Deploy.

### Backend Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | Database name (e.g., `ganaka`) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `SECRET_KEY` | Yes | JWT signing secret (32+ random bytes) |
| `ENCRYPTION_KEY` | Yes | AES-256 key (32 bytes, base64-encoded) |
| `APP_BASE_URL` | Yes | Public base URL (e.g., `https://api.your-domain.com`) |
| `SMTP_HOST` | Yes | SMTP server host |
| `SMTP_PORT` | Yes | SMTP server port (587 for TLS) |
| `SMTP_USERNAME` | Yes | SMTP username |
| `SMTP_PASSWORD` | Yes | SMTP password |
| `SMTP_FROM` | Yes | From email address |
| `SHOPIFY_API_KEY` | No | Shopify app client ID |
| `SHOPIFY_API_SECRET` | No | Shopify app client secret |
| `SHOPIFY_SCOPES` | No | OAuth scopes |
| `SHOPIFY_APP_URL` | No | Public base URL for OAuth redirect |
| `RAZORPAY_SYNC_TTL_MINUTES` | No | Razorpay sync polling interval in minutes (default 60). As of 2026-08, Razorpay `key_id`/`key_secret`/`webhook_secret` are supplied per-workspace via `POST /razorpay/connect`, not as deployment environment variables — see `ARCHITECTURE_AUDIT.md` #1 / `FIX_SUMMARY.md`. |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |

---

## 3. Frontend Deployment (Vercel)

1. Connect your repository to Vercel.
2. Import the `frontend/` directory as a new project.
3. Set environment variables:
   - `REACT_APP_BACKEND_URL` = `https://your-backend.onrender.com`
4. Deploy.

### Frontend Environment Variables

| Variable | Required | Description |
|---|---|---|
| `REACT_APP_BACKEND_URL` | Yes | Backend API URL (no trailing slash) |

---

## 4. Domain Configuration

### Backend (Render)

1. In Render dashboard, go to **Settings** → **Custom Domains**.
2. Add your custom domain (e.g., `api.your-domain.com`).
3. Update DNS:
   - Type: `CNAME`
   - Name: `api`
   - Value: `<your-service>.onrender.com`
4. Enable **Automatic HTTPS**.

### Frontend (Vercel)

1. In Vercel dashboard, go to **Settings** → **Domains**.
2. Add your custom domain (e.g., `app.your-domain.com`).
3. Update DNS:
   - Type: `A` or `CNAME`
   - Name: `app`
   - Value: `<your-vercel-deployment>.vercel.app` or Vercel's IPs
4. Vercel automatically provisions HTTPS.

---

## 5. Shopify App Configuration

1. Go to [Shopify Partners](https://partners.shopify.com) → Apps → Your App.
2. Set **App URL** to `https://api.your-domain.com`.
3. Set **Redirection URLs** to `https://api.your-domain.com/api/v1/shopify/callback`.
4. Set **Webhook URLs**:
   - `https://api.your-domain.com/api/v1/shopify/webhooks` for all webhook topics.
5. Copy **Client ID** and **Client Secret** into backend environment variables.
6. Set scopes: `read_orders,read_products,read_customers`.

---

## 6. Razorpay Configuration

1. Go to [Razorpay Dashboard](https://dashboard.razorpay.com/) → Settings → API Keys.
2. Generate **Key ID** and **Key Secret**.
3. Copy into backend environment variables.
4. Set webhook URL: `https://api.your-domain.com/api/v1/razorpay/webhooks` (if using webhooks).

---

## 7. Google OAuth Configuration (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create OAuth 2.0 Client ID.
3. Add authorized redirect URI: `https://api.your-domain.com/api/v1/auth/google/callback`.
4. Copy **Client ID** and **Client Secret** into backend environment variables.

---

## 8. SMTP Configuration

1. Choose an SMTP provider (SendGrid, Mailgun, AWS SES, etc.).
2. Create SMTP credentials.
3. Copy into backend environment variables:
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_FROM`

---

## 9. Post-Deployment Verification

1. **Health check:** `curl https://api.your-domain.com/api/v1/health`
2. **Database health:** `curl https://api.your-domain.com/api/v1/health/database`
3. **Register a test user** via the frontend.
4. **Create a workspace** and verify workspace isolation.
5. **Connect Shopify** and run a test sync.
6. **Connect Razorpay** and run a test sync.
7. **Run reconciliation** and verify results.
8. **View dashboard** and verify charts load.
9. **Export a report** and verify download.

---

## 10. Rollback Procedure

### Backend (Render)

1. Go to Render dashboard → Your Service → **Deploys**.
2. Click **Rollback** on the previous successful deploy.
3. Render will redeploy the previous commit.

### Frontend (Vercel)

1. Go to Vercel dashboard → Your Project → **Deployments**.
2. Click **...** on the previous deployment → **Promote to Production**.
3. Vercel will roll back to that deployment.

### Database

- MongoDB Atlas has automated backups. Restore from a snapshot if needed.
- See `docs/17_BACKUP_AND_DISASTER_RECOVERY.md` for RTO/RPO targets.

---

## 11. Monitoring

- **Render:** Built-in logs and metrics. Set up alerts for high CPU/memory.
- **Vercel:** Built-in analytics and logs.
- **MongoDB Atlas:** Built-in performance advisor and alerts.
- **Application:** Structured logs are emitted; connect to a log aggregation service (e.g., Datadog, ELK).

---

## 12. Security Checklist

- [ ] `SECRET_KEY` is 32+ random bytes, never committed
- [ ] `ENCRYPTION_KEY` is 32 bytes base64-encoded, never committed
- [ ] `CORS_ORIGINS` is set to production domain only (not `*`)
- [ ] HTTPS is enabled on both backend and frontend
- [ ] MongoDB requires authentication
- [ ] MongoDB network access is restricted to application IPs
- [ ] SMTP credentials are secure
- [ ] Shopify/Razorpay/Google secrets are secure
- [ ] Rate limiting is active
- [ ] Audit logging is active
- [ ] Webhook HMAC verification is enabled

---

## 13. Scaling Considerations

- **Render:** Upgrade to higher-tier plan or enable auto-scaling.
- **Vercel:** Automatically scales; no action needed.
- **MongoDB Atlas:** Upgrade cluster tier; enable read replicas for read-heavy workloads.
- **Rate limiting:** Current implementation is per-instance. For multi-instance deployments, replace with a distributed token bucket (Redis).

---

## 14. Troubleshooting

### Backend won't start

- Check Render logs for missing environment variables.
- Verify MongoDB connection string is correct.
- Verify `SECRET_KEY` and `ENCRYPTION_KEY` are set.

### Frontend shows blank page

- Check browser console for errors.
- Verify `REACT_APP_BACKEND_URL` is set correctly.
- Verify CORS origins include the frontend domain.

### Shopify OAuth fails

- Verify `SHOPIFY_APP_URL` matches the app URL in Shopify Partners.
- Verify redirect URI is registered in Shopify Partners.
- Verify `ENCRYPTION_KEY` is set and consistent across restarts.

### Razorpay sync fails

- Verify the workspace has connected its own Razorpay account via the app UI (`POST /razorpay/connect`) — as of 2026-08 there is no deployment-level Razorpay credential to check.
- Verify the connected account's key_id/key_secret are still valid and active in the Razorpay dashboard.

### Emails not sending

- Verify SMTP credentials are correct.
- Check Render logs for SMTP errors.
- Verify `SMTP_FROM` is a valid sender address.

---

## 15. Support

For issues and questions, contact the Ganaka team or refer to:
- `docs/` — specification set
- `implementation/` — milestone implementation specs
- `VERIFIED.md` — engineering verification report
- `IMPLEMENTATION_REPORT.md` — milestone reports