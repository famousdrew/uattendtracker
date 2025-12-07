# Railway Deployment Quick Start Guide

Fast-track guide for deploying Product Issue Miner to Railway. Full details available in DEPLOYMENT.md.

## 5-Minute Setup

### 1. Create Railway Project

1. Go to https://railway.app and sign in
2. Click "Create New Project"
3. Select "Deploy from GitHub"
4. Connect your GitHub account and select the repository
5. Railway creates your project

### 2. Add Managed Services (5 minutes)

In your Railway project dashboard:

#### Add PostgreSQL
```
Click: + New Service > PostgreSQL
Wait: ~30 seconds for deployment
Copy: DATABASE_URL from Variables tab
```

#### Add Redis
```
Click: + New Service > Redis
Wait: ~20 seconds for deployment
Copy: REDIS_URL from Variables tab
```

### 3. Deploy Backend Service (3 minutes)

```
Click: + New Service > GitHub Repo
Select: This repository
Root Directory: backend/
Wait: ~2 minutes for build and deploy
```

Set environment variables in Backend service > Variables tab:
```
ZENDESK_SUBDOMAIN = workwelltech
ZENDESK_EMAIL = dclark@workwelltech.com
ZENDESK_API_TOKEN = <get from Zendesk Admin API panel>
ANTHROPIC_API_KEY = <get from https://console.anthropic.com>
DASHBOARD_PASSWORD = <create strong password>
```

**Copy the backend public URL** (from Connect tab, e.g., https://product-issue-miner-backend.up.railway.app)

### 4. Deploy Frontend Service (3 minutes)

```
Click: + New Service > GitHub Repo
Select: This repository
Root Directory: frontend/
Wait: ~2 minutes for build and deploy
```

Set environment variables in Frontend service > Variables tab:
```
NEXT_PUBLIC_API_URL = <paste backend URL from step 3>
NEXT_PUBLIC_ZENDESK_SUBDOMAIN = workwelltech
```

### 5. Verify Deployment (1 minute)

Test backend health check:
```
https://<your-backend-url>/health
```

Should return:
```json
{"status": "healthy", "service": "product-issue-miner-api", "version": "1.0.0"}
```

Visit frontend:
```
https://<your-frontend-url>
```

Done! Application is live.

## Getting Required Credentials

### Zendesk API Token

1. Log in to your Zendesk account
2. Click Admin icon (gear)
3. Go to Apps and Integrations > API
4. Click Tokens tab
5. Click "Add token"
6. Enter token name: "Product Issue Miner"
7. Click "Create"
8. Copy the token immediately (you won't see it again)

### Anthropic API Key

1. Go to https://console.anthropic.com
2. Sign in or create account
3. Click "API Keys" in left sidebar
4. Click "Create Key"
5. Name it: "Product Issue Miner Railway"
6. Copy the key immediately

## Common URLs

After deployment, you'll have:

```
Backend API:  https://<project>-backend.up.railway.app
Frontend:     https://<project>-frontend.up.railway.app

API Docs:     https://<project>-backend.up.railway.app/docs
Health Check: https://<project>-backend.up.railway.app/health
```

## Troubleshooting Quick Fixes

### Backend won't deploy
1. Check: Variables tab has all required environment variables
2. Check: Build logs for errors (Deployments tab)
3. Check: PostgreSQL service is running (green status)

### Frontend shows blank page
1. Check: `NEXT_PUBLIC_API_URL` is set correctly
2. Check: Backend service is running and accessible
3. Clear browser cache and reload

### API returns 404 errors
1. Check: Backend health check works
2. Check: Frontend has correct backend URL
3. Check: Backend service port is 8000

### Database connection failed
1. Check: `DATABASE_URL` is set in Backend Variables
2. Check: PostgreSQL service shows green status
3. Click PostgreSQL service > Connect tab to verify URL

## Deployment Dashboard

In Railway project dashboard, you can:

- **View Status:** Green circle = Running
- **View Logs:** Click service > Logs tab
- **View Metrics:** Click service > Metrics tab
- **Update Variables:** Click service > Variables tab
- **Redeploy:** Deployments tab > Redeploy button
- **Rollback:** Deployments tab > Click previous deployment > Revert

## Next Steps

1. **Initial Data:** Trigger Zendesk ticket sync via API
2. **Custom Domain:** Configure your own domain in Project Settings > Domains
3. **Monitoring:** Set up alerts if available
4. **Backups:** Verify PostgreSQL auto-backups are enabled

## Full Documentation

See DEPLOYMENT.md for:
- Detailed step-by-step guide
- Post-deployment setup
- Monitoring and troubleshooting
- Backup and recovery procedures
- Custom domain configuration

See ENV_VARIABLES.md for:
- Complete environment variable reference
- Variable descriptions and usage
- Security best practices
- Troubleshooting checklist

## Support

- Railway Docs: https://docs.railway.app
- Railway Status: https://status.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com
- Next.js Docs: https://nextjs.org/docs

## Key Files

- `backend/Dockerfile` - Backend container configuration
- `backend/railway.toml` - Backend Railway-specific settings
- `frontend/Dockerfile` - Frontend container configuration
- `frontend/railway.toml` - Frontend Railway-specific settings
- `DEPLOYMENT.md` - Full deployment guide
- `ENV_VARIABLES.md` - Environment variable reference
