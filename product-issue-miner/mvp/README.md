# Product Issue Miner - MVP

A tool to extract and analyze product issues from Zendesk support tickets using Claude AI, specifically configured for uAttend time & attendance platform.

## Live Dashboard

**Production URL:** https://uattendtracker-production-b043.up.railway.app/

## Features

- Syncs tickets from Zendesk (filtered by brand)
- Analyzes tickets with Claude AI to extract product issues
- Dark mode dashboard with real-time sync updates
- Rich issue context for Product teams
- PostgreSQL storage in production

## Issue Extraction

Claude extracts the following for each issue:

| Field | Description |
|-------|-------------|
| `category` | TIMECLOCK_HARDWARE, PUNCH_SYNC, TIMECARD, PAYROLL, MOBILE_APP, etc. |
| `issue_type` | bug, friction, feature_request, data_issue, documentation_gap, configuration |
| `severity` | critical, high, medium, low |
| `summary` | One-line description |
| `detail` | Full explanation with context |
| `user_segment` | admin, manager, or employee affected |
| `platform` | Device model (BN6500, MN1000) or app (mobile, web) |
| `frequency` | one_time, intermittent, consistent |
| `has_workaround` | Whether support provided a workaround |
| `root_cause_hint` | AI hypothesis about root cause |
| `business_impact` | Operational impact description |
| `related_feature` | Specific feature affected |

## Quick Start (Local Development)

1. **Install dependencies:**
   ```bash
   cd product-issue-miner/mvp
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   export ZENDESK_SUBDOMAIN=workwelltech
   export ZENDESK_EMAIL=your-email@company.com
   export ZENDESK_API_TOKEN=your-token
   export ZENDESK_BRAND_ID=1260802408910  # uAttend brand
   export ANTHROPIC_API_KEY=your-key
   ```

3. **Run the API:**
   ```bash
   python api.py
   ```

4. **Open dashboard:** http://localhost:8000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/health` | GET | Health check |
| `/api/sync` | POST | Trigger sync (`{"days": 7}`) |
| `/api/sync/status` | GET | Check sync status |
| `/api/summary` | GET | Issue statistics |
| `/api/issues` | GET | List issues (params: `limit`, `category`, `severity`) |
| `/api/tickets` | GET | List synced tickets |
| `/api/data` | DELETE | Clear all data (for re-sync) |

## Railway Deployment

### Project Setup

1. Create new Railway project from GitHub repo
2. Set root directory to `product-issue-miner/mvp`
3. Set builder to `Dockerfile`
4. Add PostgreSQL service
5. Link `DATABASE_URL` variable from Postgres to app

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENDESK_SUBDOMAIN` | Yes | `workwelltech` |
| `ZENDESK_EMAIL` | Yes | Agent email for API auth |
| `ZENDESK_API_TOKEN` | Yes | Zendesk API token |
| `ZENDESK_BRAND_ID` | Yes | `1260802408910` (uAttend) |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `DATABASE_URL` | Yes | PostgreSQL connection (from Railway) |

### Auto-Deploy

Push to `master` branch triggers automatic deployment via Railway's GitHub integration.

## Architecture

```
mvp/
├── api.py              # FastAPI server
├── analyzer.py         # Claude issue extraction
├── config.py           # Environment config
├── knowledge_base.py   # Help Center scraper for context
├── storage.py          # SQLite/PostgreSQL storage
├── zendesk_client.py   # Zendesk API client
├── static/
│   └── index.html      # Vue.js dashboard
├── Dockerfile          # Production container
├── requirements.txt    # Python dependencies
└── railway.toml        # Railway build config
```

## Knowledge Base

The analyzer fetches article data from the uAttend Help Center (https://uattend.zendesk.com/hc/en-us) to provide product context to Claude. This helps with:

- Accurate categorization using product terminology
- Understanding device models (BN, MN, CB, JR, DR series)
- Recognizing feature areas (punch sync, fingerprint enrollment, etc.)

Cache refreshes every 7 days automatically.

## Ticket Volume & Limits

- Zendesk search API limits to 1000 results per query
- With ~240 tickets/day, we fetch in 3-day chunks
- This ensures all tickets are captured for any date range

## Data Flow

1. **Sync**: Fetch tickets from Zendesk API (paginated, chunked)
2. **Store**: Save tickets and comments to database
3. **Analyze**: Send unanalyzed tickets to Claude with Help Center context
4. **Extract**: Parse Claude response for structured issue data
5. **Display**: Show issues in dashboard with filters and detail view

## Future Improvements

- [ ] Scheduled sync (cron/background worker)
- [ ] CSV/Excel export
- [ ] Trend analysis over time
- [ ] Slack/email notifications for critical issues
- [ ] Issue clustering/deduplication
- [ ] User authentication
