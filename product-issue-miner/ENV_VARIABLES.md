# Environment Variables Reference

Complete documentation of all environment variables for the Product Issue Miner application.

## Backend Environment Variables

### Required Environment Variables

#### Zendesk Configuration

```
ZENDESK_SUBDOMAIN=workwelltech
```
- **Type:** String
- **Description:** Zendesk subdomain used for API calls (e.g., 'company' for company.zendesk.com)
- **Default:** workwelltech
- **Used by:** Zendesk API client to construct API URLs

```
ZENDESK_EMAIL=dclark@workwelltech.com
```
- **Type:** String
- **Description:** Email address of Zendesk account user for API authentication
- **Default:** None (required)
- **Used by:** Zendesk API authentication

```
ZENDESK_API_TOKEN=<your-zendesk-api-token>
```
- **Type:** String (Secret)
- **Description:** API token for Zendesk authentication
- **Retrieval:**
  1. Log in to Zendesk admin panel
  2. Go to Settings > API (or Admin > Channels > API)
  3. Click "Tokens" tab
  4. Create new token or copy existing
- **Permissions Required:**
  - View tickets
  - Read ticket comments
  - View users
- **Default:** None (required)
- **Security:** This is a secret - never commit to version control

#### Anthropic Configuration

```
ANTHROPIC_API_KEY=sk-ant-<your-api-key>
```
- **Type:** String (Secret)
- **Description:** API key for Anthropic Claude AI services
- **Retrieval:**
  1. Go to https://console.anthropic.com
  2. Navigate to API keys section
  3. Create new key or copy existing
- **Model Used:** claude-3 (or latest available)
- **Permissions Required:**
  - Messages API access
- **Default:** None (required)
- **Security:** This is a secret - never commit to version control

#### Database Configuration

```
DATABASE_URL=postgresql+asyncpg://user:password@hostname:5432/database
```
- **Type:** String
- **Format:** PostgreSQL async connection string
- **Description:** Connection string for PostgreSQL database with asyncpg driver
- **Components:**
  - `postgresql+asyncpg://` - Protocol for async PostgreSQL
  - `user` - Database user (default: postgres in Railway)
  - `password` - Database password (auto-generated in Railway)
  - `hostname` - Database host (Railway provides this)
  - `5432` - Standard PostgreSQL port
  - `database` - Database name (default: railway)
- **Railway Auto-Provision:** Yes - automatically set when PostgreSQL service added
- **Default:** None (required)
- **Security:** Contains credentials - store securely

#### Application Configuration

```
DASHBOARD_PASSWORD=<secure-password>
```
- **Type:** String (Secret)
- **Description:** Password for dashboard access and admin functions
- **Requirements:**
  - Minimum 12 characters
  - Mix of uppercase, lowercase, numbers, and symbols recommended
- **Default:** None (required)
- **Security:** This is a secret - use strong password

### Optional Environment Variables

#### Redis Configuration

```
REDIS_URL=redis://default:password@hostname:6379
```
- **Type:** String
- **Format:** Redis connection string
- **Description:** Connection string for Redis cache and job queue
- **Components:**
  - `redis://` - Protocol
  - `default` - Username (default for Railway)
  - `password` - Redis password (auto-generated in Railway)
  - `hostname` - Redis host (Railway provides this)
  - `6379` - Standard Redis port
- **Railway Auto-Provision:** Yes - automatically set when Redis service added
- **Default:** None (optional - app works without caching)
- **Used for:**
  - Caching API responses
  - Job queues for background tasks
  - Rate limiting
- **Note:** If not provided, caching is disabled but app still functions

#### Frontend URL (CORS)

```
FRONTEND_URL=https://product-issue-miner-frontend.up.railway.app
```
- **Type:** String (URL)
- **Description:** Frontend application URL for CORS configuration
- **Format:** Full HTTPS URL with domain
- **Railway Example:** `https://<service-name>.up.railway.app`
- **Custom Domain Example:** `https://app.yourdomain.com`
- **Default:** None (optional)
- **Used for:** CORS headers and API response security

#### API Base URL

```
API_BASE_URL=https://product-issue-miner-backend.up.railway.app
```
- **Type:** String (URL)
- **Description:** Base URL for API endpoints
- **Format:** Full HTTPS URL with domain
- **Default:** None (optional)
- **Used for:** Generating API documentation URLs and swagger URLs

## Frontend Environment Variables

### Required Variables (Public)

These variables are prefixed with `NEXT_PUBLIC_` and are embedded in the client bundle.

#### API URL Configuration

```
NEXT_PUBLIC_API_URL=https://product-issue-miner-backend.up.railway.app
```
- **Type:** String (URL)
- **Description:** Backend API base URL for all client-side requests
- **Format:** Full HTTPS URL without trailing slash
- **Railway Example:** `https://<backend-service>.up.railway.app`
- **Custom Domain Example:** `https://api.yourdomain.com`
- **Local Development:** `http://localhost:8000`
- **Default:** `http://localhost:8000`
- **Visibility:** Public (embedded in frontend code)
- **Used for:** All API calls from Next.js pages and components

### Optional Variables (Public)

#### Zendesk Configuration

```
NEXT_PUBLIC_ZENDESK_SUBDOMAIN=workwelltech
```
- **Type:** String
- **Description:** Zendesk subdomain for frontend display
- **Default:** workwelltech
- **Visibility:** Public (embedded in frontend code)
- **Used for:** Display tickets, links to Zendesk portal, etc.

## Getting Service URLs from Railway

### For Backend Service URL

1. Open Railway project dashboard
2. Click "Backend" service
3. Go to "Connect" tab or service settings
4. Look for "Public Domain" or "URL"
5. Format: `https://product-issue-miner-backend-production.up.railway.app`

### For Frontend Service URL

1. Click "Frontend" service in Railway dashboard
2. Go to "Connect" tab or service settings
3. Look for "Public Domain" or "URL"
4. Format: `https://product-issue-miner-frontend-production.up.railway.app`

## Environment Variable Configuration in Railway

### Step-by-Step: Setting Variables

1. Open Railway project dashboard
2. Click on the service (Backend or Frontend)
3. Go to "Variables" tab
4. Click "Add Variable"
5. Enter key and value
6. Click "Add"
7. Repeat for all variables
8. Service will auto-redeploy with new variables

### Auto-Provided by Railway Services

These variables are automatically set by Railway services:

#### From PostgreSQL Service
```
DATABASE_URL=postgresql+asyncpg://...
```
- Automatically created when PostgreSQL service is added
- No manual configuration needed

#### From Redis Service
```
REDIS_URL=redis://...
```
- Automatically created when Redis service is added
- No manual configuration needed

## Variable Validation

### Backend Validation

The backend application validates environment variables on startup:
- Missing required variables cause startup failure
- Check logs for validation errors
- All variables must be properly formatted

### Configuration Source

Backend loads configuration from:
1. Environment variables (highest priority)
2. `.env` file (local development only)
3. Default values (where applicable)

## Security Best Practices

### For Production (Railway)

1. **Never commit secrets to GitHub**
   - `.env` files should be in `.gitignore`
   - API keys should only be in Railway UI

2. **Use Railway's UI for secrets**
   - Enter sensitive values through Railway dashboard
   - They are encrypted at rest

3. **Rotate credentials regularly**
   - Zendesk API tokens: Quarterly minimum
   - Anthropic API keys: When needed or compromised
   - Database passwords: According to security policy

4. **Use least-privilege tokens**
   - Zendesk: Only grant read access needed
   - Anthropic: Limit to specific models if possible

5. **Environment isolation**
   - Use separate API keys for different environments
   - Don't share production credentials

### For Local Development

1. Create `.env` file (never commit to git)
   ```bash
   ZENDESK_SUBDOMAIN=workwelltech
   ZENDESK_EMAIL=dev@workwelltech.com
   ZENDESK_API_TOKEN=<dev-token>
   ANTHROPIC_API_KEY=<dev-key>
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/pim_dev
   REDIS_URL=redis://localhost:6379
   DASHBOARD_PASSWORD=dev-password
   FRONTEND_URL=http://localhost:3000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_ZENDESK_SUBDOMAIN=workwelltech
   ```

2. Add to `.gitignore`
   ```
   .env
   .env.local
   .env.*.local
   ```

## Troubleshooting

### Backend Won't Start

Check these variables:
- [ ] `ZENDESK_API_TOKEN` - Valid and not expired
- [ ] `ANTHROPIC_API_KEY` - Valid and has API access
- [ ] `DATABASE_URL` - Correct format and accessible
- [ ] `DASHBOARD_PASSWORD` - Set and not empty

### Frontend Shows API Errors

Check these variables:
- [ ] `NEXT_PUBLIC_API_URL` - Correct and accessible
- [ ] Backend service is running
- [ ] Check browser console for exact error

### Database Connection Failed

Check:
- [ ] `DATABASE_URL` format is correct
- [ ] PostgreSQL service is running (Railway dashboard)
- [ ] Credentials in URL match actual database

### Missing Variables Error

1. Check Railway service settings
2. Verify all required variables are added
3. Click "Variable" tab to see all set variables
4. Look for any validation errors

## Environment Profiles

### Development Profile

```bash
# Local development with defaults
ZENDESK_SUBDOMAIN=workwelltech
ANTHROPIC_API_KEY=<dev-key>
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/pim_dev
DASHBOARD_PASSWORD=dev-password
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Staging Profile

```bash
# Staging deployment (if separate from production)
ZENDESK_SUBDOMAIN=workwelltech
ANTHROPIC_API_KEY=<staging-key>
DATABASE_URL=<staging-postgres-url>
REDIS_URL=<staging-redis-url>
DASHBOARD_PASSWORD=<staging-password>
FRONTEND_URL=<staging-frontend-url>
NEXT_PUBLIC_API_URL=<staging-backend-url>
```

### Production Profile

```bash
# Production Railway deployment
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=dclark@workwelltech.com
ZENDESK_API_TOKEN=<prod-token>
ANTHROPIC_API_KEY=<prod-key>
DATABASE_URL=<railway-postgres-url>
REDIS_URL=<railway-redis-url>
DASHBOARD_PASSWORD=<prod-password>
FRONTEND_URL=<prod-frontend-url>
API_BASE_URL=<prod-backend-url>
NEXT_PUBLIC_API_URL=<prod-backend-url>
NEXT_PUBLIC_ZENDESK_SUBDOMAIN=workwelltech
```

## Quick Reference

### Backend - Required Variables
| Variable | Type | Source |
|----------|------|--------|
| ZENDESK_SUBDOMAIN | String | Fixed |
| ZENDESK_EMAIL | String | Zendesk Account |
| ZENDESK_API_TOKEN | Secret | Zendesk API |
| ANTHROPIC_API_KEY | Secret | Anthropic Console |
| DATABASE_URL | Secret | Railway PostgreSQL |
| DASHBOARD_PASSWORD | Secret | Generate yourself |

### Backend - Optional Variables
| Variable | Type | Source |
|----------|------|--------|
| REDIS_URL | Secret | Railway Redis |
| FRONTEND_URL | URL | Frontend service |
| API_BASE_URL | URL | Generate yourself |

### Frontend - Required Variables
| Variable | Type | Source |
|----------|------|--------|
| NEXT_PUBLIC_API_URL | URL | Backend service |

### Frontend - Optional Variables
| Variable | Type | Source |
|----------|------|--------|
| NEXT_PUBLIC_ZENDESK_SUBDOMAIN | String | Fixed |
