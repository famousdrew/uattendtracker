# Railway Configuration Reference

Complete configuration reference for Product Issue Miner on Railway platform.

## Project Structure Overview

```
product-issue-miner/
├── backend/                      # FastAPI backend service
│   ├── Dockerfile               # Container image definition
│   ├── railway.toml             # Railway service configuration
│   ├── requirements.txt          # Python dependencies
│   ├── alembic.ini              # Database migration config
│   ├── alembic/                 # Database migrations
│   └── app/                     # Application code
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Configuration/settings
│       ├── database.py          # Database setup
│       ├── api/                 # API endpoints
│       ├── models/              # Database models
│       ├── schemas/             # Pydantic schemas
│       └── services/            # Business logic
│
├── frontend/                     # Next.js frontend service
│   ├── Dockerfile               # Container image definition
│   ├── railway.toml             # Railway service configuration
│   ├── next.config.js           # Next.js configuration
│   ├── package.json             # Node.js dependencies
│   ├── tsconfig.json            # TypeScript configuration
│   └── src/                     # React/Next.js code
│
├── docker-compose.yml           # Local development (not used on Railway)
├── DEPLOYMENT.md                # Full deployment guide
├── RAILWAY_QUICKSTART.md        # Fast-track setup guide
├── ENV_VARIABLES.md             # Environment variable reference
└── RAILWAY_CONFIG.md            # This file
```

## Railway Services Configuration

### Service Topology

```
┌─────────────────────────────────────────────────────────┐
│                   Railway Project                        │
├──────────────────┬──────────────────┬──────────────────┤
│  PostgreSQL      │    Redis         │    Backend       │
│  (Managed)       │    (Managed)     │    (Deployed)    │
│  port: 5432      │    port: 6379    │    port: 8000    │
└──────────┬───────┴────────┬─────────┴────────┬─────────┘
           │                │                  │
           └────────────────┴──────────────────┤
                                              │
                                         ┌────▼────────┐
                                         │  Frontend    │
                                         │  (Deployed)  │
                                         │ port: 3000   │
                                         └──────────────┘
```

## Dockerfile Specifications

### Backend Dockerfile

**Location:** `backend/Dockerfile`

**Base Image:** `python:3.11-slim`
- Lightweight Python 3.11 runtime
- ~170MB base image size

**Build Stages:**
1. Install system dependencies (gcc for compiled packages)
2. Install Python dependencies from requirements.txt
3. Copy application code and migrations
4. Create non-root user (appuser, UID 1000)
5. Set up health check

**Key Features:**
- Multi-layer build for efficiency
- Non-root user for security
- Health check configured for Railway
- Environment variables for Python optimization
- Alembic migrations run on startup

**Build Time:** ~2-3 minutes (depends on dependency installation)

**Final Image Size:** ~350-400MB

### Frontend Dockerfile

**Location:** `frontend/Dockerfile`

**Build Strategy:** Multi-stage build

**Stage 1 - Builder:**
- Base: `node:20-alpine`
- Install dependencies with `npm ci`
- Build Next.js app with `npm run build`
- Creates `.next/standalone` output

**Stage 2 - Runner:**
- Base: `node:20-alpine` (fresh, lightweight image)
- Copy built application from builder stage
- Copy static assets and public folder
- Create non-root user (nextjs, UID 1001)
- Set up health check

**Key Features:**
- Multi-stage keeps final image small
- No build tools in production image
- Only necessary files copied to runner
- Non-root user for security
- Health check for Railway

**Build Time:** ~3-4 minutes (includes npm install and build)

**Final Image Size:** ~150-200MB

## Railway.toml Configuration

### Backend Railway.toml

**File:** `backend/railway.toml`

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
port = 8000
healthcheckPath = "/health"
healthcheckTimeout = 30
healthcheckInterval = 10
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

**Configuration Details:**

- **builder:** Uses Dockerfile (not Buildpacks)
- **dockerfilePath:** Relative to service root (backend/)
- **port:** Exposed port for service
- **healthcheckPath:** Health check endpoint
- **healthcheckTimeout:** Max 30 seconds for health check response
- **healthcheckInterval:** Check every 10 seconds
- **restartPolicyType:** Automatically restart on failure
- **restartPolicyMaxRetries:** Max 3 restart attempts
- **startCommand:** Custom startup command

### Frontend Railway.toml

**File:** `frontend/railway.toml`

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
port = 3000
healthcheckPath = "/"
healthcheckTimeout = 30
healthcheckInterval = 10
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
startCommand = "node server.js"
```

**Configuration Details:**

- **port:** Next.js runs on port 3000
- **healthcheckPath:** Root path check
- **startCommand:** Runs standalone Next.js server

## Environment Variable Management

### Variables in Railway Dashboard

Access via: Service > Variables tab

#### Backend Variables Setup

**Required (no defaults):**
- `ZENDESK_API_TOKEN` - From Zendesk admin API
- `ANTHROPIC_API_KEY` - From Anthropic console
- `DASHBOARD_PASSWORD` - Create yourself

**Auto-provided by Railway:**
- `DATABASE_URL` - From PostgreSQL service
- `REDIS_URL` - From Redis service

**Fixed values:**
- `ZENDESK_SUBDOMAIN = workwelltech`
- `ZENDESK_EMAIL = dclark@workwelltech.com`

**Optional:**
- `FRONTEND_URL` - For CORS (can leave blank)
- `API_BASE_URL` - For documentation (can leave blank)

#### Frontend Variables Setup

**Required:**
- `NEXT_PUBLIC_API_URL` - Backend public URL

**Fixed values:**
- `NEXT_PUBLIC_ZENDESK_SUBDOMAIN = workwelltech`

### Variable Propagation

- Variables set in Railway UI are injected at runtime
- For frontend: Build-time environment variables embedded in bundle
- For backend: Runtime environment variables loaded from environment
- Changes require service redeploy to take effect

## Port Mapping

### Network Configuration

```
┌────────────────────────────────────────────┐
│      Railway Internal Network              │
├─────────────────┬──────────┬──────────────┤
│ PostgreSQL:5432 │ Redis:6379 │ Backend:8000 │
└─────────────────┴──────────┴──────────────┘
                      │
                      └──────────┐
                                 │
                    ┌────────────▼─────────────┐
                    │  Internet Gateway        │
                    │ (Railway Load Balancer)  │
                    └────────────┬─────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
  ┌─────▼─────┐        ┌────────▼────────┐      ┌───────▼──────┐
  │ Backend    │        │  Frontend       │      │ PostgreSQL   │
  │ Public URL │        │  Public URL     │      │ (Private)    │
  └───────────┘        └─────────────────┘      └──────────────┘
```

## Database Configuration

### PostgreSQL Service

**Railway Auto-Provisioning:**
- Service name: PostgreSQL (auto-created)
- Version: Latest stable
- Database: `railway`
- User: `postgres`
- Password: Auto-generated, secure

**Connection Details:**
- Hostname: Railway-provided (internal or public)
- Port: 5432 (standard PostgreSQL)
- Database: `railway`
- Pool size: 5 (configured in database.py)
- Max overflow: 10 (for peak load)
- SSL: By default on Railway

**Connection URL:**
```
postgresql+asyncpg://postgres:PASSWORD@HOSTNAME:5432/railway
```

**Backup Configuration:**
- Auto-backups enabled by default
- Retention: Configurable in Railway
- Access: Available in PostgreSQL service settings

### Redis Service

**Railway Auto-Provisioning:**
- Service name: Redis (auto-created)
- Version: Latest stable
- Port: 6379 (standard Redis)
- Password: Auto-generated, secure

**Connection Details:**
- Hostname: Railway-provided
- Port: 6379
- Database: 0 (default)
- Protocol: redis:// or rediss:// (with TLS)

**Connection URL:**
```
redis://default:PASSWORD@HOSTNAME:6379/0
```

**Purpose:**
- Caching API responses
- Job queue for background tasks
- Rate limiting
- Session storage (if used)

**Optional:** If not used, remove `REDIS_URL` and app still works

## Build Configuration

### Backend Build Process

1. **Trigger:** Push to GitHub or manual trigger
2. **Fetch Code:** Clone repository
3. **Build Context:** `/backend` directory
4. **Dockerfile:** `backend/Dockerfile`
5. **Build Steps:**
   - Base image pull: `python:3.11-slim`
   - Install system deps: gcc
   - Install Python deps: pip install -r requirements.txt
   - Copy code: app/, alembic/, alembic.ini
   - Create user: appuser
   - Build cache: Layer caching
6. **Push:** Image stored in Railway registry
7. **Deploy:** Container started with environment variables

**Build Time:** 2-3 minutes
**Cache:** Docker layer caching enabled

### Frontend Build Process

1. **Trigger:** Push to GitHub or manual trigger
2. **Fetch Code:** Clone repository
3. **Build Context:** `/frontend` directory
4. **Dockerfile:** `frontend/Dockerfile`
5. **Build Steps:**
   - Stage 1 (Builder):
     - Base: `node:20-alpine`
     - Install: npm ci
     - Build: npm run build
     - Output: `.next/standalone`
   - Stage 2 (Runner):
     - Base: `node:20-alpine`
     - Copy: .next/standalone + static + public
     - Create: nextjs user
6. **Push:** Image stored in Railway registry
7. **Deploy:** Container started

**Build Time:** 3-4 minutes
**Optimization:** Multi-stage reduces final image by 75%

## Deployment Process

### Step-by-Step Deployment

1. **Service Creation:**
   ```
   Railway Project > + New Service > GitHub Repo
   Select Repository > Select Root Directory
   ```

2. **Build Trigger:**
   ```
   Auto-triggers on push to main/default branch
   Or manual trigger via "Redeploy" button
   ```

3. **Build Phase:**
   ```
   Download source
   Run Dockerfile build
   Run health checks
   Tag image
   ```

4. **Deploy Phase:**
   ```
   Inject environment variables
   Start container
   Wait for health check to pass
   Route traffic to service
   ```

5. **Verification:**
   ```
   Check Deployments tab
   View logs in Logs tab
   Test health endpoint
   ```

### Deployment Timeframe

- **Total:** 5-7 minutes per service
- **Build:** 2-4 minutes
- **Deploy:** 1-2 minutes
- **Health Check:** 30-60 seconds

## Health Checks

### Backend Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "product-issue-miner-api",
  "version": "1.0.0"
}
```

**Configuration:**
- Path: `/health`
- Timeout: 30 seconds
- Interval: 10 seconds
- Passes after: 1 successful check
- Fails after: 3 failed checks (restarts)

### Frontend Health Check

**Endpoint:** `GET /`

**Response:** HTML page (or redirect)

**Configuration:**
- Path: `/`
- Timeout: 30 seconds
- Interval: 10 seconds
- Method: HTTP GET
- Accepts any 2xx status code

## Auto-Scaling Configuration

**Default Railway Behavior:**
- Automatic horizontal scaling
- Scales based on CPU/Memory usage
- Min replicas: 1
- Max replicas: (configurable)
- Cooldown: (configurable)

**Adjust in:**
1. Service settings
2. Look for "Scaling" or "Replicas" section
3. Set min/max if needed

## Networking

### Service Discovery

**Internal (within Railway):**
```
postgres:5432        (PostgreSQL hostname)
redis:6379           (Redis hostname)
backend:8000         (Backend internal address)
```

**External (public):**
```
https://<project>-backend.up.railway.app    (Backend)
https://<project>-frontend.up.railway.app   (Frontend)
```

### Domain Configuration

**Default Railway Domain:**
- Format: `https://<service-name>-<project>.up.railway.app`
- SSL: Automatic, no configuration needed
- CDN: Included by default

**Custom Domain:**
1. Project Settings > Domains
2. Add custom domain
3. Configure DNS (CNAME record)
4. Wait for SSL provisioning (~5 minutes)

## Logs and Monitoring

### View Logs

**In Railway Dashboard:**
1. Click service
2. Click "Logs" tab
3. Real-time streaming logs
4. Filter by level: Info, Warn, Error

**Log Sources:**
- **Backend:** Uvicorn logs + application logs
- **Frontend:** Next.js logs + Node.js logs
- **Services:** PostgreSQL, Redis operational logs

### Metrics Available

- CPU usage (%)
- Memory usage (MB)
- Network I/O (bytes/sec)
- Request count
- Response time

### Monitoring Best Practices

- Check logs daily
- Monitor error rate
- Track database connections
- Watch API response times
- Set up alerts (if available)

## Troubleshooting Guide

### Service Won't Start

**Check:**
1. Build logs for errors (Deployments tab)
2. Missing environment variables (Variables tab)
3. Dockerfile syntax errors
4. Dependency issues (requirements.txt, package.json)

**Common Fixes:**
- Redeploy with correct variables
- Check git repository is accessible
- Verify subdirectory paths

### Health Check Failing

**Backend:**
1. Check if `/health` endpoint exists
2. Verify database connectivity
3. Check logs for startup errors
4. Ensure all required env vars set

**Frontend:**
1. Check if `/` responds
2. Verify build succeeded
3. Check Node.js process running
4. Review build logs

### High CPU/Memory Usage

**Causes:**
- Inefficient queries
- Memory leak in application
- Too much concurrent traffic

**Solutions:**
- Check application logs
- Optimize database queries
- Increase resource limits (if available)
- Scale horizontally (add replicas)

### Database Connection Issues

1. Check `DATABASE_URL` is correct
2. Verify PostgreSQL service running
3. Check credentials in URL
4. Ensure SSL requirements met
5. Review database logs

## Cost Optimization

### Railway Pricing Tiers

1. **Pay-as-you-go:** Pay for actual usage
   - Services: $5/month base
   - Compute: $0.000417/minute
   - Database: Additional charges

2. **Railway Plus:** $20/month subscriptions
   - Included compute credits
   - Priority support
   - Additional resources

### Cost Reduction Tips

1. **Use managed services:** PostgreSQL, Redis (included)
2. **Idle timeout:** Stop unused services
3. **Monitor usage:** Check Metrics tab
4. **Optimize code:** Reduce compute time
5. **Database indexes:** Faster queries
6. **Caching:** Reduce database hits

## Backup Strategy

### PostgreSQL Backups

**Automatic:**
- Daily backups by default
- 7-day retention (configurable)
- Point-in-time recovery available

**Manual Backup:**
```bash
pg_dump "postgresql://user:pass@host:5432/database" > backup.sql
```

**Restore:**
- Contact Railway support for restore
- Or use backup file with pg_restore

### Application Backups

**Code:**
- GitHub repository is your backup
- All code in git history
- Can restore any previous version

**Configuration:**
- Environment variables: Note in secure location
- Database schema: In Alembic migrations

## Security Considerations

### Network Security

- **Internal:** All services communicate internally (no external exposure)
- **Database:** PostgreSQL not publicly accessible
- **Redis:** Redis not publicly accessible
- **API:** Only backend and frontend have public URLs

### Secret Management

- Use Railway's Variables UI for secrets
- Secrets encrypted at rest
- Never commit `.env` files to git
- Rotate API tokens regularly

### SSL/TLS

- All public URLs use HTTPS
- Railway auto-provisions SSL certificates
- Valid certificate included

### User Access

- Non-root users in containers
- PostgreSQL requires auth
- Redis protected with password
- Dashboard password required

## Deployment Checklist

Before deploying:

- [ ] All required environment variables documented
- [ ] API credentials obtained (Zendesk, Anthropic)
- [ ] Repository accessible from Railway
- [ ] Dockerfiles present and valid
- [ ] railway.toml files configured
- [ ] Port configuration correct
- [ ] Health check endpoints working
- [ ] Database migrations verified
- [ ] Frontend API URL configured correctly
- [ ] CORS settings appropriate

After deploying:

- [ ] All services show green status
- [ ] Health checks passing
- [ ] No errors in logs
- [ ] Frontend accessible
- [ ] Backend health endpoint works
- [ ] Database connected
- [ ] API responds correctly
- [ ] Frontend displays properly

## Support Resources

- Railway Docs: https://docs.railway.app
- FastAPI Documentation: https://fastapi.tiangolo.com
- Next.js Documentation: https://nextjs.org/docs
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Railway Support: support@railway.app
