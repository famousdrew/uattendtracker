# Railway Deployment - Product Issue Miner

Complete deployment package for the Product Issue Miner application on Railway platform.

## Quick Links

- **Start Here:** [RAILWAY_DEPLOYMENT_INDEX.md](RAILWAY_DEPLOYMENT_INDEX.md) - Navigation guide
- **Quick Deploy:** [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md) - 15-minute setup
- **Full Guide:** [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive guide
- **Technical Details:** [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md) - Architecture & specs
- **Environment Setup:** [ENV_VARIABLES.md](ENV_VARIABLES.md) - Variable reference
- **Architecture:** [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) - Visual diagrams
- **Summary:** [DEPLOYMENT_SUMMARY.txt](DEPLOYMENT_SUMMARY.txt) - Project summary

## What's Included

### Docker Container Configuration

Production-ready Docker images for FastAPI backend and Next.js frontend:

- `backend/Dockerfile` - Python 3.11 slim image with FastAPI, Alembic migrations, health checks
- `backend/railway.toml` - Backend service configuration for Railway platform
- `frontend/Dockerfile` - Multi-stage Node.js 20 Alpine image with Next.js
- `frontend/railway.toml` - Frontend service configuration for Railway platform
- `frontend/next.config.js` - Enhanced with security headers, optimization, and environment variables

### Managed Services

Railway automatically provides:

1. **PostgreSQL Database** - Auto-provisioning of `DATABASE_URL` environment variable
2. **Redis Cache** - Auto-provisioning of `REDIS_URL` environment variable
3. **Load Balancer & CDN** - HTTPS, SSL/TLS, auto-scaling
4. **Database Backups** - Automatic daily backups with 7-day retention

### Documentation (50K+ of guides)

| Document | Purpose | Time |
|----------|---------|------|
| RAILWAY_QUICKSTART.md | Fast-track deployment | 15 min |
| DEPLOYMENT.md | Step-by-step guide with details | 30 min |
| RAILWAY_CONFIG.md | Technical deep dive | Reference |
| ENV_VARIABLES.md | All environment variables | Reference |
| DEPLOYMENT_ARCHITECTURE.md | Visual architecture diagrams | Reference |
| RAILWAY_DEPLOYMENT_INDEX.md | Navigation guide | Reference |
| DEPLOYMENT_SUMMARY.txt | Project summary | Reference |

## Key Features

### Backend (FastAPI)
- Async database connections with asyncpg
- Automatic database migrations (Alembic)
- Health check endpoint (`/health`)
- CORS configuration for frontend
- Graceful shutdown handling
- Connection pooling (5 base + 10 overflow)
- Non-root user execution (appuser, UID 1000)

### Frontend (Next.js)
- Standalone output for Docker
- Image optimization
- Response compression
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- React strict mode
- Health check endpoint (`/`)
- Non-root user execution (nextjs, UID 1001)

### Infrastructure
- Auto-scaling ready
- Health check monitoring (every 10 seconds)
- Auto-restart on failure (max 3 retries)
- Environment variable injection
- Docker layer caching for fast builds
- Public HTTPS URLs (auto SSL provisioning)
- Custom domain support
- Database auto-backups

## Getting Started

### Step 1: Read Documentation

Start with [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md) for a 15-minute overview.

### Step 2: Gather Credentials

You'll need:
- Zendesk API token (from Zendesk Admin > API > Tokens)
- Anthropic API key (from https://console.anthropic.com)
- Create a strong dashboard password

### Step 3: Deploy

1. Create Railway project at https://railway.app
2. Add PostgreSQL service
3. Add Redis service
4. Deploy backend from GitHub
5. Deploy frontend from GitHub
6. Configure environment variables
7. Verify deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed walkthrough.

## Environment Variables

### Backend Required
- `ZENDESK_API_TOKEN` - Zendesk API authentication
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `DASHBOARD_PASSWORD` - Dashboard access password

### Backend Auto-Provided by Railway
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Backend Fixed Values
- `ZENDESK_SUBDOMAIN=workwelltech`
- `ZENDESK_EMAIL=dclark@workwelltech.com`

### Frontend Required
- `NEXT_PUBLIC_API_URL` - Backend public URL

See [ENV_VARIABLES.md](ENV_VARIABLES.md) for complete reference.

## Deployment Timeline

- **Preparation:** 5 minutes
- **Infrastructure setup:** 5 minutes
- **Backend deployment:** 3 minutes
- **Frontend deployment:** 3 minutes
- **Verification:** 5 minutes
- **Total to live:** ~21 minutes

## File Locations

```
product-issue-miner/
├── backend/
│   ├── Dockerfile          - Backend container image
│   ├── railway.toml        - Backend Railway config
│   ├── requirements.txt     - Python dependencies
│   ├── app/
│   │   ├── main.py        - FastAPI application
│   │   ├── config.py      - Settings/config
│   │   └── ...
│   └── alembic/           - Database migrations
│
├── frontend/
│   ├── Dockerfile         - Frontend container image
│   ├── railway.toml       - Frontend Railway config
│   ├── next.config.js     - Next.js config (ENHANCED)
│   ├── package.json       - Node dependencies
│   └── src/              - React/Next.js code
│
├── RAILWAY_DEPLOYMENT_INDEX.md    - Navigation guide
├── RAILWAY_QUICKSTART.md          - 15-minute setup
├── DEPLOYMENT.md                  - Full deployment guide
├── RAILWAY_CONFIG.md              - Technical reference
├── ENV_VARIABLES.md               - Variable reference
├── DEPLOYMENT_ARCHITECTURE.md     - Visual diagrams
├── DEPLOYMENT_SUMMARY.txt         - Project summary
└── README_RAILWAY.md              - This file
```

## Key Decisions Made

### Architecture
- Microservices: Separate backend API and frontend UI
- Database: PostgreSQL (managed by Railway)
- Cache: Redis (managed by Railway, optional)
- Containerization: Docker with multi-stage builds for optimization

### Deployment Strategy
- Platform: Railway (managed, scalable infrastructure)
- CI/CD: GitHub integration for auto-triggers
- Health Checks: Every 10 seconds for rapid failure detection
- Restart Policy: Automatic restart on failure (max 3 retries)

### Container Strategy
- Backend: Python 3.11 slim (~350MB)
- Frontend: Node 20 Alpine multi-stage (~150MB)
- Security: Non-root users in both containers
- Optimization: Layer caching, multi-stage builds

## Security Features

- **Containerization:** Non-root users (appuser, nextjs)
- **Network:** All services behind Railway load balancer
- **SSL/TLS:** Automatic HTTPS provisioning and renewal
- **Secrets:** Environment variables encrypted at rest
- **Database:** Password-protected, internal-only network
- **Cache:** Password-protected Redis
- **Headers:** Security headers configured in Next.js
- **Health Checks:** Continuous monitoring for availability

## Monitoring & Support

### View Logs
1. Railway dashboard > Service > Logs tab
2. Real-time streaming view
3. Filter by log level (Info, Warn, Error)

### Check Metrics
1. Railway dashboard > Service > Metrics tab
2. CPU usage, memory, network I/O
3. Request counts and response times

### Troubleshooting
See relevant section in:
- [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md) - Quick fixes
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed troubleshooting
- [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md) - Technical issues

## Support Resources

- **Railway Docs:** https://docs.railway.app
- **Railway Status:** https://status.railway.app
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Next.js Docs:** https://nextjs.org/docs
- **PostgreSQL Docs:** https://www.postgresql.org/docs/

## Success Criteria

Your deployment is successful when:

- All services show green status in Railway dashboard
- Health check endpoint returns healthy status
- Frontend is accessible via public URL
- Backend API responds correctly to requests
- Database is connected and responsive
- No errors in application logs
- Frontend can successfully communicate with backend API

## Next Steps

1. **Read:** [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md) (15 minutes)
2. **Gather:** Required credentials and API keys
3. **Deploy:** Follow [DEPLOYMENT.md](DEPLOYMENT.md) step-by-step
4. **Verify:** Test all endpoints and services
5. **Configure:** Set up custom domain (optional)
6. **Monitor:** Check logs and metrics regularly

## Common Tasks

### Deploy Application
Push changes to GitHub > Railway auto-builds and deploys

### Update Environment Variables
Railway Dashboard > Service > Variables tab > Add/edit > Auto-redeploy

### View Logs
Railway Dashboard > Service > Logs tab > Real-time view

### Rollback Deployment
Railway Dashboard > Service > Deployments > Click previous > Revert

### Scale Resources
Railway Dashboard > Service > Settings > Adjust allocation

### Add Custom Domain
Railway Dashboard > Project Settings > Domains > Add domain > Configure DNS

## Project Information

- **Application:** Product Issue Miner
- **Backend:** FastAPI (Python 3.11)
- **Frontend:** Next.js (Node 20)
- **Database:** PostgreSQL (managed)
- **Cache:** Redis (managed, optional)
- **Platform:** Railway
- **Deployment Type:** Containerized (Docker)
- **Status:** Production Ready

## Version Information

- Python: 3.11
- Node.js: 20
- FastAPI: 0.109.0
- Next.js: 14.1.0
- PostgreSQL: Latest
- Redis: Latest
- Docker: Multi-stage build

## License

This deployment configuration is part of the Product Issue Miner project.

---

**Created:** December 6, 2025
**Status:** Production Ready
**Documentation:** Complete

For additional information, see the comprehensive documentation files included in this directory.
