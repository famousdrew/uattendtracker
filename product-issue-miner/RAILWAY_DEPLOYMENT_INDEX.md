# Railway Deployment Index

Complete reference for deploying Product Issue Miner to Railway platform.

## Quick Navigation

### Getting Started

1. **New to Railway?** Start here:
   - Read: [RAILWAY_QUICKSTART.md](RAILWAY_QUICKSTART.md)
   - Time: 15 minutes to live deployment

2. **Need detailed walkthrough?** See:
   - Read: [DEPLOYMENT.md](DEPLOYMENT.md)
   - Covers: Step-by-step with screenshots
   - Time: 30 minutes for complete setup

3. **Want technical details?** Check:
   - Read: [RAILWAY_CONFIG.md](RAILWAY_CONFIG.md)
   - Covers: Architecture, specs, troubleshooting

4. **Setting up environment variables?** Reference:
   - Read: [ENV_VARIABLES.md](ENV_VARIABLES.md)
   - Covers: All variable options and descriptions

## Document Overview

### RAILWAY_QUICKSTART.md
**Purpose:** Fast-track deployment in 15 minutes

**What you'll find:**
- 5-minute service setup instructions
- Getting credentials (Zendesk, Anthropic)
- Service URL references
- Quick troubleshooting

**Best for:** Users who just want to deploy now

**Key sections:**
- 5-Minute Setup
- Getting Required Credentials
- Common URLs
- Troubleshooting Quick Fixes

---

### DEPLOYMENT.md
**Purpose:** Comprehensive deployment guide with detailed steps

**What you'll find:**
- Prerequisites and project setup
- Step-by-step service configuration
- Database setup (PostgreSQL, Redis)
- Post-deployment verification
- Complete troubleshooting guide
- Backup and recovery procedures

**Best for:** Complete walkthroughs with explanations

**Key sections:**
- Prerequisites (What you need before starting)
- Project Setup (Creating Railway project)
- Database Configuration (PostgreSQL and Redis)
- Service Deployment (Backend and Frontend)
- Post-Deployment (Data setup and domain config)
- Monitoring & Troubleshooting (Common issues and solutions)
- Scaling & Resources (Managing infrastructure)
- Backup & Recovery (Protecting your data)

---

### RAILWAY_CONFIG.md
**Purpose:** Technical configuration reference

**What you'll find:**
- Project structure overview
- Docker/container specifications
- Railway.toml configuration details
- Environment variable management
- Build and deployment processes
- Health check configuration
- Network and domain setup
- Troubleshooting guide
- Cost optimization

**Best for:** Technical deep dives and troubleshooting

**Key sections:**
- Project Structure Overview (File layout)
- Dockerfile Specifications (Container details)
- Railway.toml Configuration (Service settings)
- Build Configuration (Build process details)
- Deployment Process (Step-by-step technical flow)
- Health Checks (Monitoring configuration)
- Logs and Monitoring (Observability setup)
- Troubleshooting Guide (Technical issues)

---

### ENV_VARIABLES.md
**Purpose:** Complete environment variable reference

**What you'll find:**
- All backend environment variables
- All frontend environment variables
- Variable descriptions and formats
- How to get each variable value
- Security best practices
- Local development setup
- Environment profiles (dev/staging/prod)
- Quick reference table

**Best for:** Environment configuration and management

**Key sections:**
- Backend Environment Variables (All options)
- Frontend Environment Variables (All options)
- Getting Service URLs from Railway (How to retrieve)
- Variable Configuration in Railway (Step-by-step UI guide)
- Security Best Practices (Protecting secrets)
- Troubleshooting (Common variable issues)
- Environment Profiles (Different setups)

---

## File Organization

### Docker & Configuration Files

Location: `backend/` and `frontend/`

- `backend/Dockerfile` - FastAPI container image
- `backend/railway.toml` - Backend Railway configuration
- `frontend/Dockerfile` - Next.js container image
- `frontend/railway.toml` - Frontend Railway configuration

### Documentation Files

Location: Project root

- `RAILWAY_DEPLOYMENT_INDEX.md` - This file (navigation)
- `RAILWAY_QUICKSTART.md` - Fast-track guide
- `DEPLOYMENT.md` - Full deployment guide
- `RAILWAY_CONFIG.md` - Technical reference
- `ENV_VARIABLES.md` - Variable reference

## Deployment Timeline

### Phase 1: Preparation (5 minutes)
1. Read RAILWAY_QUICKSTART.md
2. Gather credentials:
   - Zendesk API token
   - Anthropic API key
3. Create Railway account (if needed)

### Phase 2: Infrastructure (5 minutes)
1. Create Railway project
2. Add PostgreSQL service
3. Add Redis service
4. Copy auto-generated URLs

### Phase 3: Services (10 minutes)
1. Deploy backend service
2. Set backend environment variables
3. Deploy frontend service
4. Set frontend environment variables

### Phase 4: Verification (5 minutes)
1. Test health endpoints
2. Verify database connectivity
3. Test frontend access
4. Check logs for errors

**Total Time:** 25 minutes from start to live deployment

## Key Deployment Decisions

### Service Topology

```
PostgreSQL (Managed by Railway)
    ↓
Backend (FastAPI on port 8000)
    ↓
Frontend (Next.js on port 3000)
    ↓
Redis (Managed by Railway, optional)
```

### Container Strategy

- **Backend:** Python 3.11 slim image (~350MB)
- **Frontend:** Multi-stage Node.js build (~150MB)
- Both use non-root users for security
- Both include health checks

### Environment Setup

- **Auto-provided:** DATABASE_URL, REDIS_URL
- **Required:** API keys, passwords
- **Optional:** Frontend URL, API base URL

## Common Tasks

### Deploy Application
1. Push changes to GitHub
2. Railway auto-triggers build
3. Monitor Deployments tab
4. Verify health checks pass

### Update Environment Variables
1. Go to service settings
2. Click Variables tab
3. Add/edit variable
4. Service auto-redeploys

### View Application Logs
1. Click service in dashboard
2. Go to Logs tab
3. Real-time streaming view
4. Search/filter as needed

### Scale Resources
1. Click service settings
2. Adjust CPU/Memory allocation
3. Configure auto-scaling rules
4. Changes take effect immediately

### Rollback Deployment
1. Go to Deployments tab
2. Click previous successful deployment
3. Click Revert button
4. Service restarts with old code

### Add Custom Domain
1. Go to Project Settings
2. Click Domains section
3. Add domain (e.g., yourdomain.com)
4. Configure DNS CNAME record
5. Wait for SSL provisioning

## Troubleshooting Quick Reference

| Problem | Quick Fix | Full Guide |
|---------|-----------|-----------|
| Build fails | Check Deployments logs | DEPLOYMENT.md - Build Failures |
| Can't reach API | Verify backend URL | DEPLOYMENT.md - Frontend Can't Reach Backend |
| Database error | Check DATABASE_URL | RAILWAY_CONFIG.md - Database Connection Issues |
| API returns 404 | Check health endpoint | DEPLOYMENT.md - Common Issues |
| High CPU usage | Check logs for loops | RAILWAY_CONFIG.md - High CPU/Memory Usage |
| SSL certificate missing | Configure domain | DEPLOYMENT.md - Configure Custom Domains |

## Security Checklist

Before deploying to production:

- [ ] Never commit `.env` files
- [ ] Use Railway Variables UI for secrets
- [ ] API tokens from official sources only
- [ ] Strong passwords (12+ chars, mixed types)
- [ ] Rotate credentials quarterly
- [ ] Enable database backups
- [ ] Review CORS settings
- [ ] Check security headers in next.config.js
- [ ] Monitor logs for suspicious activity
- [ ] Test backup/restore procedure

## Performance Optimization

### Backend Optimization
- Health checks configured
- Database connection pooling enabled
- Alembic migrations automated
- Non-blocking async I/O

### Frontend Optimization
- Multi-stage Docker build
- Standalone Next.js output
- Image optimization configured
- Security headers enabled
- Compression enabled

### Infrastructure Optimization
- Managed services (reduce ops)
- Auto-scaling (handle traffic)
- Health checks (quick recovery)
- Layer caching (faster builds)

## Support & Resources

### Official Documentation
- Railway Docs: https://docs.railway.app
- Railway Status: https://status.railway.app
- Railway Support: support@railway.app

### Technology Docs
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org/docs
- PostgreSQL: https://www.postgresql.org/docs/
- Docker: https://docs.docker.com/

### Getting Help
1. Check relevant guide above
2. Search Railway docs
3. Review logs in Deployments
4. Contact Railway support with:
   - Project ID
   - Service names
   - Log snippets
   - Steps to reproduce

## Deployment Checklist

### Before Deployment
- [ ] GitHub repository accessible
- [ ] Credentials obtained (Zendesk, Anthropic)
- [ ] Environment variables documented
- [ ] Dockerfiles present and valid
- [ ] Railway.toml files configured
- [ ] Next.js build configured for Docker

### During Deployment
- [ ] Services deploy in correct order
- [ ] Environment variables set
- [ ] Build completes without errors
- [ ] Health checks passing
- [ ] No errors in logs

### After Deployment
- [ ] Health endpoints responding
- [ ] Frontend displays content
- [ ] Backend API accessible
- [ ] Database connected
- [ ] Redis available (if used)
- [ ] Custom domain configured (if needed)
- [ ] Monitoring set up

## Next Steps After Deployment

1. **Verify Everything Works**
   - Test health endpoint: `/health`
   - Visit frontend in browser
   - Check logs for errors

2. **Configure Custom Domain** (Optional)
   - See: DEPLOYMENT.md - Configure Custom Domains
   - Time: 10 minutes

3. **Set Up Monitoring** (Recommended)
   - Check Metrics tab regularly
   - Set up alerts if available
   - Monitor error rates

4. **Initial Data** (If Needed)
   - Trigger Zendesk sync
   - Verify data appears
   - Check for any errors

5. **Test Backup Restoration**
   - See: DEPLOYMENT.md - Backup & Recovery
   - Verify restore procedure works
   - Test recovery process

## File Locations Reference

```
C:\dev\uattendissuetrack\product-issue-miner\
├── RAILWAY_DEPLOYMENT_INDEX.md      <- Navigation (this file)
├── RAILWAY_QUICKSTART.md             <- 15-minute setup guide
├── DEPLOYMENT.md                     <- Full deployment guide
├── RAILWAY_CONFIG.md                 <- Technical reference
├── ENV_VARIABLES.md                  <- Variable reference
├── frontend/
│   ├── Dockerfile                   <- Frontend container config
│   ├── railway.toml                 <- Frontend Railway settings
│   └── next.config.js               <- Enhanced with security headers
└── backend/
    ├── Dockerfile                   <- Backend container config
    ├── railway.toml                 <- Backend Railway settings
    ├── requirements.txt             <- Python dependencies
    └── app/
        ├── main.py                  <- FastAPI app with health check
        └── config.py                <- Settings loading
```

## Version Information

- **Python:** 3.11 (FastAPI backend)
- **Node.js:** 20 (Next.js frontend)
- **PostgreSQL:** Latest available on Railway
- **Redis:** Latest available on Railway
- **FastAPI:** 0.109.0
- **Next.js:** 14.1.0

## License & Support

This deployment configuration is provided as part of the Product Issue Miner application.

For issues:
1. Check the relevant guide above
2. Review Railway documentation
3. Check application logs
4. Contact project maintainers

---

**Last Updated:** December 6, 2025
**Status:** Production Ready
