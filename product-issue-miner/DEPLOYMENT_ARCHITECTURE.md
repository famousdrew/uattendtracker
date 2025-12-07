# Deployment Architecture Diagram

Visual reference for the Product Issue Miner deployment architecture on Railway.

## System Architecture Overview

```
                         INTERNET (Public Access)
                                 |
                    ┌────────────┼────────────┐
                    |            |            |
              HTTPS |      HTTPS |      HTTPS |
              Port  |      Port  |      Port  |
              443   |       443  |       443  |
                    |            |            |
         ┌──────────▼──┐  ┌──────▼────────┐  └─────┐
         │  Frontend    │  │  Backend API │  Custom
         │   (Next.js)  │  │  (FastAPI)   │  Domain
         │  Port 3000   │  │  Port 8000   │
         └──────────────┘  └──────────────┘
                    |            |
                    │            │
         ┌──────────┘            └───────────┐
         │                                   │
         │   Railway Internal Network        │
         │                                   │
    ┌────▼────────────────────────────────┐ │
    │                                      │ │
    │   ┌─────────────────┐  ┌─────────┐  │ │
    │   │  PostgreSQL 5432│  │Redis6379│  │ │
    │   │   (Database)    │  │(Cache)  │  │ │
    │   └────────┬────────┘  └────┬────┘  │ │
    │            │                 │      │ │
    │   ┌────────▼─────────────────▼────┐ │ │
    │   │    Backend Service (8000)     │ │ │
    │   │  - Receives API requests      │ │ │
    │   │  - Queries database           │ │ │
    │   │  - Calls Zendesk API          │ │ │
    │   │  - Calls Anthropic API        │ │ │
    │   │  - Manages business logic     │ │ │
    │   └────────────┬──────────────────┘ │ │
    │                │                    │ │
    │   ┌────────────▼───────────────┐   │ │
    │   │ Frontend Service (3000)    │   │ │
    │   │ - Serves Next.js app       │   │ │
    │   │ - Requests Backend API     │   │ │
    │   │ - Renders UI               │   │ │
    │   └────────────────────────────┘   │ │
    │                                    │ │
    └────────────────────────────────────┘ │
         │                                 │
         └─────────────────────────────────┘
```

## Service Interactions

```
USER BROWSER
     |
     | HTTPS GET /
     |
     v
┌─────────────────────┐
│  Railway Load       │
│  Balancer / CDN     │
│  (SSL termination)  │
└──────────┬──────────┘
           |
           | HTTP GET /
           |
           v
    ┌──────────────────┐
    │   Frontend       │
    │   Next.js 14.1   │
    │   Port 3000      │
    │                  │
    │  - HTML/CSS/JS   │
    │  - React/Next    │
    │  - API client    │
    └────────┬─────────┘
             |
             | HTTP POST/GET /api/*
             | with NEXT_PUBLIC_API_URL
             |
             v
    ┌──────────────────┐
    │    Backend       │
    │    FastAPI       │
    │    Port 8000     │
    │                  │
    │  - FastAPI app   │
    │  - Routes/logic  │
    └──┬─────────┬──┬──┘
       |         |  |
   DB  |Redis    |  | Zendesk
   Ops |Ops      |  | Anthropic
       |         |  |
       v         v  v
    ┌────┐  ┌────┐ ┌──────┐  ┌─────────┐
    │    │  │    │ │      │  │         │
    │ PG │  │    │ │Zendesk│ │Anthropic│
    │    │  │    │ │ API  │  │ API    │
    │    │  │    │ │      │  │        │
    └────┘  └────┘ └──────┘  └────────┘
```

## Data Flow - User Request

```
User Accesses Frontend
         |
         v
GET https://frontend.railway.app/
         |
         v
Railway serves Next.js app
         |
         v
Browser loads React/Next.js components
         |
         v
useQuery() calls API endpoint
         |
         v
HTTP POST https://backend.railway.app/api/tickets
         |
         v
Backend receives request
         |
         v
Query PostgreSQL database
         |
         v
Check Redis cache (optional)
         |
         v
Call Zendesk API (if needed)
         |
         v
Call Anthropic API (for analysis)
         |
         v
Return JSON response
         |
         v
Frontend displays data in UI
```

## Container Deployment Structure

```
Railway Project: product-issue-miner
│
├─ Service: PostgreSQL (Managed)
│  ├─ Type: Managed database
│  ├─ Version: Latest
│  ├─ Port: 5432 (internal)
│  ├─ Database: railway
│  └─ Auto-provides: DATABASE_URL
│
├─ Service: Redis (Managed)
│  ├─ Type: Managed cache
│  ├─ Version: Latest
│  ├─ Port: 6379 (internal)
│  └─ Auto-provides: REDIS_URL
│
├─ Service: Backend (Deployed from Dockerfile)
│  ├─ Source: GitHub repository
│  ├─ Dockerfile: backend/Dockerfile
│  ├─ Base image: python:3.11-slim
│  ├─ Working dir: /app
│  ├─ Port: 8000 (exposed)
│  ├─ User: appuser (non-root)
│  ├─ Health check: GET /health
│  ├─ Command: alembic upgrade head && uvicorn ...
│  ├─ Environment variables: (from Railway UI)
│  │  ├─ ZENDESK_SUBDOMAIN
│  │  ├─ ZENDESK_EMAIL
│  │  ├─ ZENDESK_API_TOKEN
│  │  ├─ ANTHROPIC_API_KEY
│  │  ├─ DATABASE_URL (auto)
│  │  ├─ REDIS_URL (auto)
│  │  ├─ DASHBOARD_PASSWORD
│  │  ├─ FRONTEND_URL
│  │  └─ API_BASE_URL
│  └─ Auto-restart: on_failure (max 3 retries)
│
└─ Service: Frontend (Deployed from Dockerfile)
   ├─ Source: GitHub repository
   ├─ Dockerfile: frontend/Dockerfile
   ├─ Build stages: 2 (builder + runner)
   ├─ Base images: node:20-alpine
   ├─ Working dir: /app
   ├─ Port: 3000 (exposed)
   ├─ User: nextjs (non-root)
   ├─ Health check: GET /
   ├─ Command: node server.js
   ├─ Environment variables: (from Railway UI)
   │  ├─ NEXT_PUBLIC_API_URL
   │  └─ NEXT_PUBLIC_ZENDESK_SUBDOMAIN
   └─ Auto-restart: on_failure (max 3 retries)
```

## Build Process Flow

### Backend Build

```
GitHub Code
    |
    v
Railway Webhook Trigger
    |
    v
Clone Repository
    |
    v
Navigate to backend/
    |
    v
Docker Build (Dockerfile)
    |
    ├─ FROM python:3.11-slim
    ├─ WORKDIR /app
    ├─ Install gcc
    ├─ RUN pip install -r requirements.txt
    ├─ COPY app, alembic, alembic.ini
    ├─ CREATE appuser (uid 1000)
    ├─ HEALTHCHECK /health
    │
    v
Docker Image (~350MB)
    |
    v
Push to Railway Registry
    |
    v
Start Container
    |
    ├─ Inject env variables
    ├─ RUN alembic upgrade head (migrations)
    ├─ Start uvicorn server
    │
    v
Health Check (GET /health)
    |
    ├─ Fails? Restart (max 3 times)
    ├─ Passes? Mark healthy
    │
    v
Route traffic to service
```

### Frontend Build

```
GitHub Code
    |
    v
Railway Webhook Trigger
    |
    v
Clone Repository
    |
    v
Navigate to frontend/
    |
    v
Docker Build (Multi-stage)
    |
    ├─ STAGE 1: Builder
    │  ├─ FROM node:20-alpine
    │  ├─ npm ci (clean install)
    │  ├─ npm run build
    │  ├─ Create .next/standalone
    │  │
    ├─ STAGE 2: Runner
    │  ├─ FROM node:20-alpine (fresh)
    │  ├─ COPY from builder: .next/standalone
    │  ├─ COPY from builder: .next/static, public
    │  ├─ CREATE nextjs user (uid 1001)
    │  ├─ HEALTHCHECK /
    │  │
    v
Docker Image (~150MB)
    |
    v
Push to Railway Registry
    |
    v
Start Container
    |
    ├─ Inject env variables
    ├─ Start node server.js
    │
    v
Health Check (GET /)
    |
    ├─ Fails? Restart (max 3 times)
    ├─ Passes? Mark healthy
    │
    v
Route traffic to service
```

## Deployment Timeline

```
Time    Action                          Status
───────────────────────────────────────────────
0 min   User clicks "Deploy"
        - GitHub webhook triggered

1 min   Backend build starts
        - Clone code
        - Download base image
        - Install dependencies

3 min   Backend image ready
        - Push to registry
        - Start container
        - Run migrations

5 min   Backend health check passes
        - Container marked healthy
        - Traffic routed to service

5 min   Frontend build starts
        - Clone code
        - Multi-stage build
        - Download base images

7 min   Frontend image ready
        - Push to registry
        - Start container

8 min   Frontend health check passes
        - Container marked healthy
        - Traffic routed to service

10 min  BOTH SERVICES LIVE
        - Frontend accessible
        - Backend API responding
        - Database connected
        - Cache available
```

## Network Communication

```
External:
  User  ---HTTPS---> Railway Load Balancer
                          |
         ┌────────────────┼───────────────┐
         |                |               |
    HTTP|/               HTTP|/api/*     HTTP|/
         |                |               |
         v                v               v
    Frontend          Backend           Custom
    (3000)            (8000)            Domain

Internal (Railway):
  Frontend <---HTTP---> Backend
  (3000)     (8000)    (8000)
     |                    |
     |                    ├──> PostgreSQL (5432)
     |                    ├──> Redis (6379)
     |                    ├──> Zendesk API
     |                    └──> Anthropic API
     |
     └──> Serves static assets from /public
          Handles client-side routing
          Communicates with Backend API
```

## Environment Variable Injection

```
Railway Dashboard Variables UI
         |
         ├─ Backend Service
         │  ├─ ZENDESK_SUBDOMAIN
         │  ├─ ZENDESK_EMAIL
         │  ├─ ZENDESK_API_TOKEN (secret)
         │  ├─ ANTHROPIC_API_KEY (secret)
         │  ├─ DATABASE_URL (auto from PostgreSQL)
         │  ├─ REDIS_URL (auto from Redis)
         │  ├─ DASHBOARD_PASSWORD (secret)
         │  ├─ FRONTEND_URL
         │  └─ API_BASE_URL
         │       |
         │       v
         │  Container Runtime Environment
         │  Loaded by: app/config.py
         │  Used by: FastAPI app
         │
         └─ Frontend Service
            ├─ NEXT_PUBLIC_API_URL
            └─ NEXT_PUBLIC_ZENDESK_SUBDOMAIN
                 |
                 v
            Build-time substitution
            Embedded in Next.js bundle
            Available in browser as window.env
```

## Auto-Restart Strategy

```
Container Health Check
         |
         ├─ Every 10 seconds
         |
         v
GET /health endpoint
         |
    ┌────┴─────┐
    |          |
  Pass       Fail
    |          |
    v          v
Continue  Add Retry
Running   (max 3 retries)
              |
              └─> All failed?
                    |
                    v
                  Restart Container
                    |
                    v
                  Run startup command
                    |
                    v
                  Health check again
                    |
                  ┌─┴─┐
                  |   |
                Pass Fail
                  |   |
                  v   v
              Serve API  Back to restart loop
```

## Backup & Recovery

```
PostgreSQL Auto-Backup
         |
         ├─ Interval: Daily
         ├─ Retention: 7 days
         |
         v
Backup stored in Railway
         |
    ┌────┴──────┐
    |           |
 Point-in-time  Manual Restore
    Restore        |
    |              v
    |         Contact Railway
    |         Provide backup ID
    |              |
    v              v
Database state    Database restored
  recovered       to selected time
```

## Security Layers

```
Internet Request
    |
    v
Railway Firewall
    |
    v
Load Balancer (DDoS protection)
    |
    v
HTTPS Termination (TLS 1.3)
    |
    v
Container Network
    |
    ├─ Frontend (non-root user)
    ├─ Backend (non-root user)
    ├─ PostgreSQL (authenticated only)
    └─ Redis (password protected)
         |
         v
Environment Variables (encrypted at rest)
         |
         v
Secret Rotation (best practice)
```

## Traffic Flow Example

```
User interacts with Frontend:
"Get all tickets"

1. Frontend (React component)
   GET /api/tickets

2. Load Balancer
   Route to backend.railway.app

3. Backend Container
   Uvicorn receives request
   FastAPI router processes
   Session created from pool

4. Database Query
   SELECT * FROM tickets
   PostgreSQL returns rows

5. Cache Check
   Check Redis for similar queries
   Maybe cache this result

6. Response Assembly
   Serialize to JSON
   Add headers (CORS, security)

7. Response Sent
   HTTP 200 JSON array
   Load balancer sends to frontend

8. Frontend Renders
   useQuery receives data
   React re-renders list
   User sees tickets

Time taken: ~100-500ms (cached) or ~500ms-2s (uncached with AI processing)
```

## Scaling Architecture

```
Single Instance (Default)
┌─────────────────────┐
│  Frontend (1 copy)  │
│  Backend (1 copy)   │
│  PostgreSQL (1)     │
│  Redis (1)          │
└─────────────────────┘

If CPU/Memory exceeds threshold:
         |
         v
Railway Auto-Scales
         |
    ┌────┴────┐
    |         |
  Scale      Scale
 Frontend    Backend
    |         |
    v         v
┌──────┐   ┌──────┐
│FE #1 │   │BE #1 │
│FE #2 │   │BE #2 │
│FE #3 │   │BE #3 │
└──────┘   └──────┘
    |         |
    v         v
Load balanced across copies
Database & Redis shared (single instance)

Static content (JS/CSS): Cached at CDN
API calls: Round-robin across backend copies
Database: Single PostgreSQL instance (can be scaled separately)
```

## Summary

This architecture provides:
- **High availability** through auto-restart and health checks
- **Scalability** through containerization and auto-scaling
- **Security** through non-root users, HTTPS, and secret management
- **Reliability** through managed PostgreSQL with backups
- **Performance** through Redis caching and CDN
- **Developer experience** through GitHub integration and auto-deployment
