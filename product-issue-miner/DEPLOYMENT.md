# Railway Deployment Guide - Product Issue Miner

This guide provides step-by-step instructions for deploying the Product Issue Miner application to Railway.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Database Configuration](#database-configuration)
4. [Service Deployment](#service-deployment)
5. [Environment Variables](#environment-variables)
6. [Post-Deployment](#post-deployment)
7. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository with this project
- Required API credentials:
  - Zendesk API token
  - Anthropic API key
- Docker knowledge (for local testing)

## Project Setup

### Step 1: Create Railway Project

1. Log in to [Railway](https://railway.app)
2. Click "Create New Project"
3. Select "Deploy from GitHub"
4. Authorize Railway with GitHub access
5. Select the repository containing this project

### Step 2: Add Services

All services will be added to the same Railway project. Follow the order below.

## Database Configuration

### Step 3: Add PostgreSQL Database

1. In your Railway project, click "+ New Service"
2. Select "PostgreSQL" from the list
3. Railway will automatically create the service with:
   - Database name: `railway`
   - Username: `postgres`
   - Auto-generated secure password
   - Version: Latest PostgreSQL

4. Once deployed, Railway provides `DATABASE_URL` environment variable automatically
5. Note this URL for backend configuration

### Step 4: Add Redis Cache

1. Click "+ New Service"
2. Select "Redis" from the list
3. Railway will create Redis service with:
   - Default port: 6379
   - Auto-generated password

4. Once deployed, Railway provides `REDIS_URL` environment variable automatically
5. Note this URL for backend configuration

## Service Deployment

### Step 5: Deploy Backend Service

1. Click "+ New Service" > "GitHub Repo"
2. Select your repository and choose the `/backend` subdirectory
3. Railway will auto-detect the Dockerfile

#### Backend Configuration:

1. **Service Settings:**
   - Set name: `product-issue-miner-backend`
   - Port: `8000` (auto-detected from Dockerfile)

2. **Build Settings:**
   - Builder: Dockerfile (auto-detected)
   - Root Directory: `backend/`

3. **Environment Variables:**
   Add all variables listed in [Environment Variables - Backend](#backend-environment-variables)

4. **Deploy:**
   - Railway will automatically trigger build and deploy
   - Monitor build logs in the "Deployments" tab
   - Once green, service is ready

### Step 6: Deploy Frontend Service

1. Click "+ New Service" > "GitHub Repo"
2. Select your repository and choose the `/frontend` subdirectory
3. Railway will auto-detect the Dockerfile

#### Frontend Configuration:

1. **Service Settings:**
   - Set name: `product-issue-miner-frontend`
   - Port: `3000` (auto-detected from Dockerfile)

2. **Build Settings:**
   - Builder: Dockerfile (auto-detect)
   - Root Directory: `frontend/`

3. **Environment Variables:**
   Add all variables listed in [Environment Variables - Frontend](#frontend-environment-variables)

   **Important:** For `NEXT_PUBLIC_API_URL`, use the full URL of your backend service:
   - Get from Backend service details: `https://<backend-service-name>.up.railway.app`

4. **Deploy:**
   - Railway will build and deploy
   - Wait for deployment to complete

## Environment Variables

### Backend Environment Variables

Configure these in the Backend service settings:

```
# Zendesk Configuration (REQUIRED)
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=dclark@workwelltech.com
ZENDESK_API_TOKEN=<your-zendesk-api-token>

# Anthropic Configuration (REQUIRED)
ANTHROPIC_API_KEY=<your-anthropic-api-key>

# Database (AUTO from PostgreSQL service)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/database

# Redis (AUTO from Redis service)
REDIS_URL=redis://default:pass@host:6379

# Application Configuration
DASHBOARD_PASSWORD=<secure-password-for-dashboard>
FRONTEND_URL=https://<frontend-railway-url>
API_BASE_URL=https://<backend-railway-url>
```

### Frontend Environment Variables

Configure these in the Frontend service settings:

```
# API Configuration (REQUIRED)
NEXT_PUBLIC_API_URL=https://<backend-railway-url>

# Zendesk Configuration
NEXT_PUBLIC_ZENDESK_SUBDOMAIN=workwelltech
```

**Note:** Railway automatically provides these environment variables:
- PostgreSQL service provides: `DATABASE_URL`
- Redis service provides: `REDIS_URL`

### How to Get Service URLs

1. Go to your Railway project dashboard
2. Click on the Backend service
3. In "Connect" or "Settings" tab, find the public URL
4. Copy the full URL (e.g., `https://service-name.up.railway.app`)
5. Use this in Frontend's `NEXT_PUBLIC_API_URL`

## Post-Deployment

### Step 7: Initial Data Setup

After all services are deployed:

1. **Verify Connectivity:**
   - Test backend health check: `https://<backend-url>/health`
   - Should return: `{"status": "healthy", "service": "product-issue-miner-api", "version": "1.0.0"}`

2. **Run Database Migrations:**
   - Migrations run automatically on backend startup (via `alembic upgrade head`)
   - Check backend logs to confirm migrations succeeded

3. **Initial Data Backfill (if needed):**
   - Connect to backend via API
   - Trigger Zendesk ticket sync
   - Monitor progress in backend logs

### Step 8: Configure Custom Domains (Optional)

1. In Railway project settings
2. Click "Domains"
3. For Backend:
   - Add domain (e.g., `api.yourdomain.com`)
   - Configure DNS as instructed
4. For Frontend:
   - Add domain (e.g., `yourdomain.com`)
   - Configure DNS as instructed

## Monitoring & Troubleshooting

### View Logs

1. In Railway project, click on service
2. Go to "Logs" tab
3. View real-time logs for debugging

### Common Issues

#### Database Connection Failed
- **Symptom:** Backend logs show connection errors
- **Solution:**
  - Verify `DATABASE_URL` is set correctly
  - Check PostgreSQL service is running (green status)
  - Verify credentials are correct

#### Redis Connection Issues
- **Symptom:** Cache operations fail, but app still works
- **Solution:**
  - Verify `REDIS_URL` is set correctly
  - Check Redis service is running
  - Redis is optional; app will work without it

#### Frontend Can't Reach Backend
- **Symptom:** Frontend shows API errors
- **Solution:**
  - Verify `NEXT_PUBLIC_API_URL` is correct
  - Check backend service is running
  - Ensure CORS is properly configured in backend
  - Backend main.py allows `["*"]` for development

#### Build Failures
- **Symptom:** Deployment failed, red X in dashboard
- **Solution:**
  - Check build logs for specific error
  - Verify all required environment variables are set
  - Ensure Dockerfile is in correct location
  - Verify subdirectory is correctly specified

### Deployment Status

Check service status:
1. Click service in Railway dashboard
2. Look at:
   - Green circle = Running
   - Yellow circle = Deploying
   - Red circle = Failed
3. Click "Deployments" to see history
4. View logs for any errors

### Performance Monitoring

1. In service details, view:
   - CPU usage
   - Memory usage
   - Network I/O
2. Adjust resource allocation if needed
3. Set up alerts if Railway supports it

## Database Migrations

Database migrations run automatically via Alembic on backend startup:

```bash
alembic upgrade head
```

To view migration status:
1. Check backend logs during startup
2. Look for "Running migrations..." messages
3. Verify "migrations completed successfully"

## Scaling & Resources

Railway automatically handles:
- Auto-scaling based on traffic
- Container restart on failure
- Load balancing

To manually adjust:
1. Click service in dashboard
2. Go to "Settings"
3. Adjust resource allocation
4. Configure restart policies

## Secrets Management

Best practices for secrets in Railway:

1. **Never commit secrets to GitHub**
2. Use Railway's environment variable UI
3. For additional security:
   - Use Railway's built-in secret management
   - Rotate API keys regularly
   - Use least-privilege API tokens

## Backup & Recovery

### Database Backups

Railway PostgreSQL includes automatic backups:
1. Go to PostgreSQL service
2. Check "Backups" section
3. Configure backup retention policy

### Restore Procedure

1. Contact Railway support for backup restore
2. Or use manual backup via:
   ```bash
   pg_dump postgresql://user:pass@host/db > backup.sql
   ```

## Monitoring Checklist

Regular tasks:
- [ ] Check service status daily
- [ ] Monitor API response times
- [ ] Review error logs weekly
- [ ] Update dependencies monthly
- [ ] Rotate API keys quarterly
- [ ] Test backup restoration process

## Support & Resources

- Railway Documentation: https://docs.railway.app
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- Next.js Docker: https://nextjs.org/docs/deployment/docker
- PostgreSQL Backups: https://docs.railway.app/databases/postgresql

## Rollback Procedure

If deployment fails:

1. In Railway project, click service
2. Go to "Deployments" tab
3. Find last working deployment
4. Click "Revert to this deployment"
5. Confirm rollback

## Troubleshooting Checklist

Before contacting support:
- [ ] Verify all environment variables are set
- [ ] Check service logs for errors
- [ ] Verify database connectivity
- [ ] Test health check endpoint
- [ ] Check if third-party services (Zendesk, Anthropic) are accessible
- [ ] Review recent code changes
- [ ] Check Railway status page for incidents
