# Product Issue Miner - MVP

A minimal tool to extract product issues from Zendesk support tickets using Claude AI.

## Quick Start (Local)

1. **Install dependencies:**
   ```bash
   cd mvp
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Test connections:**
   ```bash
   python main.py test
   ```

4. **Sync and analyze:**
   ```bash
   python main.py sync --days 7 --limit 50
   python main.py analyze
   python main.py report --details
   ```

## CLI Commands

| Command | Description |
|---------|-------------|
| `test` | Test Zendesk and Claude connections |
| `sync --days N --limit M` | Fetch tickets from last N days (max M) |
| `analyze` | Analyze unprocessed tickets with Claude |
| `report [--details]` | Show summary report |
| `clear [--issues]` | Clear database or just issues |

## Web API

Run the API server:
```bash
python api.py
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/test` | GET | Test connections |
| `/api/sync` | POST | Trigger sync (body: `{"days": 7, "limit": 100}`) |
| `/api/sync/status` | GET | Check sync status |
| `/api/summary` | GET | Get issue statistics |
| `/api/issues` | GET | List issues (params: `limit`, `category`, `severity`) |
| `/api/tickets` | GET | List tickets |

## Deploy to Railway via GitHub

### One-time Setup

1. **Create Railway project:**
   - Go to [Railway](https://railway.app)
   - Create new project
   - Link your GitHub repo

2. **Add environment variables in Railway:**
   - `ZENDESK_SUBDOMAIN`
   - `ZENDESK_EMAIL`
   - `ZENDESK_API_TOKEN`
   - `ZENDESK_BRAND_ID` (optional)
   - `ANTHROPIC_API_KEY`

3. **Get Railway token:**
   - Go to Account Settings > Tokens
   - Create a new token

4. **Add GitHub secrets:**
   - Go to your repo Settings > Secrets > Actions
   - Add `RAILWAY_TOKEN` with your token

5. **Push to master** - deploys automatically!

### Manual Deploy
```bash
# Or trigger via GitHub Actions UI (workflow_dispatch)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ZENDESK_SUBDOMAIN` | Yes | Your Zendesk subdomain |
| `ZENDESK_EMAIL` | Yes | Agent email for API auth |
| `ZENDESK_API_TOKEN` | Yes | Zendesk API token |
| `ZENDESK_BRAND_ID` | No | Filter to specific brand |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `PORT` | No | API port (default: 8000) |

## Data Storage

MVP uses SQLite (`mvp_data.db`) for simplicity. For production:
- Use Railway's PostgreSQL addon
- Or mount a persistent volume

## Limitations (MVP)

- SQLite (single instance only)
- No auth on API
- Simple keyword clustering (no embeddings)
- No scheduled sync (manual trigger only)

Upgrade path: Add PostgreSQL, auth, and cron job for production.
