# Product Issue Miner - Technical Implementation Spec

## Overview

Internal tool to extract and categorize product issues from Zendesk tickets. Analyzes ~5,000 tickets/month using Claude Sonnet 4.5, clusters similar issues, surfaces trends via web dashboard.

**Stack**: Python (FastAPI) + Next.js + PostgreSQL + Redis  
**Hosting**: Railway  
**AI**: Claude Sonnet 4.5 via Anthropic API

---

## Product Taxonomy

```python
CATEGORIES = {
    "TIME_AND_ATTENDANCE": [
        "hardware_issues",       # Physical device problems, connectivity
        "punch_in_out",          # Clock actions, missed punches
        "biometric_registration",# Fingerprint/face enrollment
        "pto",                   # PTO requests, balances, accruals
        "reporting",             # T&A reports, exports
        "corrections"            # Timecard edits, approvals
    ],
    "PAYROLL": [
        "pay_runs",              # Processing payroll, failures
        "tax_questions",         # Withholding, filings, W2/1099
        "direct_deposits",       # Bank setup, failed deposits
        "reporting",             # Payroll reports, exports
        "errors"                 # Calculation errors, system errors
    ],
    "SETTINGS": [
        "employee_registration", # Adding new employees
        "biometric_enrollment",  # Fingerprint/face setup
        "deductions"             # Benefits, garnishments
    ]
}

ISSUE_TYPES = [
    "bug",              # Broken functionality
    "friction",         # Works but painful
    "ux_confusion",     # User doesn't understand how
    "feature_request",  # Wants capability that doesn't exist
    "documentation_gap",# Couldn't find answer in docs
    "data_issue"        # Sync, import/export problems
]

SEVERITIES = ["critical", "high", "medium", "low"]
```

---

## Project Structure

```
product-issue-miner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings from env
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── ticket.py
│   │   │   ├── issue.py
│   │   │   └── cluster.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── ticket.py
│   │   │   └── issue.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── zendesk.py          # Zendesk API client
│   │   │   ├── analyzer.py         # Claude integration
│   │   │   ├── clusterer.py        # Issue grouping
│   │   │   └── sync.py             # Orchestrates pipeline
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── issues.py
│   │   │   ├── clusters.py
│   │   │   └── tickets.py
│   │   └── tasks/
│   │       ├── __init__.py
│   │       └── worker.py           # Background job runner
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Dashboard home
│   │   │   ├── layout.tsx
│   │   │   ├── clusters/
│   │   │   │   ├── page.tsx        # Cluster list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx    # Cluster detail
│   │   │   └── api/                # API route proxies if needed
│   │   ├── components/
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── ClusterTable.tsx
│   │   │   ├── TicketTable.tsx
│   │   │   └── Filters.tsx
│   │   └── lib/
│   │       └── api.ts              # Backend API client
│   ├── package.json
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── railway.toml
├── docker-compose.yml              # Local dev
└── README.md
```

---

## Database Schema

```sql
-- Stores raw ticket data from Zendesk
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zendesk_ticket_id BIGINT UNIQUE NOT NULL,
    subject VARCHAR(500),
    description TEXT,
    internal_notes TEXT,
    public_comments TEXT,
    requester_email VARCHAR(255),
    requester_org_name VARCHAR(255),
    zendesk_org_id BIGINT,
    tags JSONB DEFAULT '[]',
    status VARCHAR(50),
    priority VARCHAR(50),
    ticket_created_at TIMESTAMP NOT NULL,
    ticket_updated_at TIMESTAMP NOT NULL,
    synced_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP,
    
    CONSTRAINT idx_tickets_zd_id UNIQUE (zendesk_ticket_id)
);
CREATE INDEX idx_tickets_updated ON tickets(ticket_updated_at);
CREATE INDEX idx_tickets_analyzed ON tickets(analyzed_at);

-- Individual issues extracted from tickets (0-N per ticket)
CREATE TABLE extracted_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    issue_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    detail TEXT,
    representative_quote TEXT,
    cluster_id UUID REFERENCES issue_clusters(id) ON DELETE SET NULL,
    confidence DECIMAL(3,2),
    extracted_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_category CHECK (category IN ('TIME_AND_ATTENDANCE', 'PAYROLL', 'SETTINGS')),
    CONSTRAINT chk_severity CHECK (severity IN ('critical', 'high', 'medium', 'low'))
);
CREATE INDEX idx_issues_category ON extracted_issues(category, subcategory);
CREATE INDEX idx_issues_severity ON extracted_issues(severity);
CREATE INDEX idx_issues_cluster ON extracted_issues(cluster_id);
CREATE INDEX idx_issues_extracted ON extracted_issues(extracted_at);

-- Grouped clusters of similar issues
CREATE TABLE issue_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    cluster_name VARCHAR(200) NOT NULL,
    cluster_summary TEXT,
    issue_count INT DEFAULT 0,
    unique_customers INT DEFAULT 0,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    count_7d INT DEFAULT 0,
    count_prior_7d INT DEFAULT 0,
    trend_pct DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    pm_status VARCHAR(50) DEFAULT 'new',
    pm_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_clusters_category ON issue_clusters(category, subcategory);
CREATE INDEX idx_clusters_active ON issue_clusters(is_active, issue_count DESC);

-- Tracks sync progress for incremental updates
CREATE TABLE sync_state (
    id SERIAL PRIMARY KEY,
    last_ticket_updated_at TIMESTAMP NOT NULL,
    tickets_synced INT DEFAULT 0,
    issues_extracted INT DEFAULT 0,
    sync_completed_at TIMESTAMP DEFAULT NOW()
);
```

---

## Environment Variables

```bash
# Zendesk
ZENDESK_SUBDOMAIN=yourcompany          # yourcompany.zendesk.com
ZENDESK_EMAIL=api-user@company.com
ZENDESK_API_TOKEN=xxxxxxxxxxxxxxxx

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# Database (Railway provides this)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (Railway provides this)
REDIS_URL=redis://default:pass@host:6379

# App
API_BASE_URL=https://your-backend.railway.app
FRONTEND_URL=https://your-frontend.railway.app
```

---

## API Endpoints

### Backend (FastAPI)

```
GET  /health                         # Health check

# Issues
GET  /api/issues                     # List issues (paginated, filterable)
     ?category=TIME_AND_ATTENDANCE
     ?subcategory=punch_in_out
     ?issue_type=bug
     ?severity=critical,high
     ?cluster_id=uuid
     ?start_date=2024-09-01
     ?end_date=2024-12-01
     ?search=clock
     ?page=1&per_page=50

GET  /api/issues/summary             # Aggregated stats for dashboard
     ?days=7

# Clusters  
GET  /api/clusters                   # List clusters
     ?category=TIME_AND_ATTENDANCE
     ?is_active=true
     ?sort=issue_count:desc
     ?page=1&per_page=20

GET  /api/clusters/{id}              # Cluster detail with issues
PATCH /api/clusters/{id}             # Update pm_status, pm_notes
     Body: { "pm_status": "reviewed", "pm_notes": "..." }

# Tickets
GET  /api/tickets/{zendesk_id}       # Single ticket with extracted issues

# Export
GET  /api/export/issues              # CSV download (same filters as /issues)
GET  /api/export/clusters            # CSV download

# Admin/Debug
POST /api/sync/trigger               # Manually trigger sync
GET  /api/sync/status                # Last sync info
```

---

## Zendesk API Integration

### Authentication
```python
# Basic auth with email/token
# Header: Authorization: Basic base64(email/token:api_token)
```

### Endpoints Used

```python
# Search tickets updated since last sync
GET /api/v2/search.json?query=type:ticket updated>{last_sync_date}&sort_by=updated_at&sort_order=asc

# Get single ticket with comments (sideload comments)
GET /api/v2/tickets/{id}.json?include=comment_count

# Get all comments for a ticket (includes internal notes if authenticated as admin)
GET /api/v2/tickets/{id}/comments.json

# Rate limits: 700 requests/minute
```

### Sync Logic

```python
def sync_tickets(backfill_days: int = None):
    """
    Incremental sync: fetch tickets updated since last sync.
    Backfill mode: fetch all tickets from last N days.
    """
    last_sync = get_last_sync_timestamp()  # From sync_state table
    
    if backfill_days:
        start_date = datetime.now() - timedelta(days=backfill_days)
    else:
        start_date = last_sync or (datetime.now() - timedelta(days=1))
    
    query = f"type:ticket updated>{start_date.isoformat()}"
    
    for ticket_batch in paginate_search(query, page_size=100):
        for ticket in ticket_batch:
            # Fetch full ticket with comments
            full_ticket = fetch_ticket_with_comments(ticket['id'])
            
            # Separate internal vs public comments
            internal_notes = [c for c in full_ticket['comments'] if not c['public']]
            public_comments = [c for c in full_ticket['comments'] if c['public']]
            
            # Upsert to database
            upsert_ticket(
                zendesk_ticket_id=ticket['id'],
                subject=ticket['subject'],
                description=ticket['description'],
                internal_notes=format_comments(internal_notes),
                public_comments=format_comments(public_comments),
                requester_email=ticket['requester']['email'],
                requester_org_name=ticket.get('organization', {}).get('name'),
                zendesk_org_id=ticket.get('organization_id'),
                tags=ticket['tags'],
                status=ticket['status'],
                priority=ticket['priority'],
                ticket_created_at=ticket['created_at'],
                ticket_updated_at=ticket['updated_at']
            )
    
    update_sync_state(last_ticket_updated_at=datetime.now())
```

---

## Claude Integration

### Issue Extraction Prompt

```python
EXTRACTION_SYSTEM_PROMPT = """You are a product analyst for a time & attendance + payroll SaaS company.
Analyze support tickets to extract product issues for the PM team.

PRODUCT TAXONOMY:
Categories: TIME_AND_ATTENDANCE, PAYROLL, SETTINGS

Subcategories:
- TIME_AND_ATTENDANCE: hardware_issues, punch_in_out, biometric_registration, pto, reporting, corrections
- PAYROLL: pay_runs, tax_questions, direct_deposits, reporting, errors
- SETTINGS: employee_registration, biometric_enrollment, deductions

Issue types: bug, friction, ux_confusion, feature_request, documentation_gap, data_issue

Severity:
- critical: Money/compliance issues, complete blockers
- high: Major workflow blocked, workaround painful
- medium: Impaired but functional
- low: Minor inconvenience

INSTRUCTIONS:
1. Read the ticket (subject, description, all comments including internal notes)
2. Identify DISTINCT product issues (0 if none, multiple if several issues)
3. Ignore pure support process issues (refund requests, account access, billing)
4. Use representative quotes that capture user pain

Respond with JSON only:
{
  "issues": [
    {
      "category": "TIME_AND_ATTENDANCE",
      "subcategory": "punch_in_out",
      "issue_type": "bug",
      "severity": "high",
      "summary": "Clock-in button unresponsive on Android app after OS update",
      "detail": "Multiple users reporting the clock-in button requires 3-4 taps after updating to Android 14.",
      "representative_quote": "My employees have to tap the button multiple times",
      "confidence": 0.92
    }
  ],
  "no_product_issue": false,
  "skip_reason": null
}

If no product issues:
{
  "issues": [],
  "no_product_issue": true,
  "skip_reason": "Billing inquiry only"
}"""

def build_extraction_user_prompt(ticket: dict) -> str:
    return f"""Analyze this ticket:

TICKET ID: {ticket['zendesk_ticket_id']}
SUBJECT: {ticket['subject']}
CREATED: {ticket['ticket_created_at']}
REQUESTER: {ticket['requester_email']} ({ticket['requester_org_name'] or 'No org'})
TAGS: {', '.join(ticket['tags']) if ticket['tags'] else 'None'}

DESCRIPTION:
{ticket['description'] or 'No description'}

PUBLIC COMMENTS:
{ticket['public_comments'] or 'None'}

INTERNAL NOTES:
{ticket['internal_notes'] or 'None'}"""
```

### Cluster Naming Prompt

```python
CLUSTER_NAMING_PROMPT = """Given a group of related product issues, generate a specific cluster name and summary.

Good names are specific and actionable:
✓ "Android 14 clock-in button tap delay"
✓ "CA state tax withholding errors"

Bad names are vague:
✗ "Mobile app issues"
✗ "Tax problems"

Respond with JSON:
{
  "cluster_name": "Specific name (max 100 chars)",
  "cluster_summary": "2-3 sentence summary of the issue pattern and business impact"
}"""

def build_cluster_naming_prompt(issues: list) -> str:
    summaries = "\n".join([f"- {i['summary']}" for i in issues[:20]])
    quotes = "\n".join([f'- "{i["representative_quote"]}"' for i in issues[:10] if i.get('representative_quote')])
    
    return f"""Category: {issues[0]['category']}
Subcategory: {issues[0]['subcategory']}
Number of tickets: {len(issues)}

Issue summaries:
{summaries}

Representative quotes:
{quotes}"""
```

### API Call

```python
import anthropic

client = anthropic.Anthropic()

def extract_issues(ticket: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": build_extraction_user_prompt(ticket)}
        ],
        system=EXTRACTION_SYSTEM_PROMPT
    )
    return json.loads(response.content[0].text)

def name_cluster(issues: list) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=256,
        messages=[
            {"role": "user", "content": build_cluster_naming_prompt(issues)}
        ],
        system=CLUSTER_NAMING_PROMPT
    )
    return json.loads(response.content[0].text)
```

---

## Clustering Logic

```python
def cluster_issues():
    """
    Group issues by category + subcategory, then by similarity.
    Simple approach: keyword overlap + exact summary matching.
    """
    # Get unclustered issues
    unclustered = db.query(ExtractedIssue).filter(
        ExtractedIssue.cluster_id.is_(None)
    ).all()
    
    # Group by category + subcategory
    grouped = defaultdict(list)
    for issue in unclustered:
        key = (issue.category, issue.subcategory)
        grouped[key].append(issue)
    
    for (category, subcategory), issues in grouped.items():
        # Find existing active clusters for this category
        existing_clusters = db.query(IssueCluster).filter(
            IssueCluster.category == category,
            IssueCluster.subcategory == subcategory,
            IssueCluster.is_active == True
        ).all()
        
        for issue in issues:
            matched_cluster = find_matching_cluster(issue, existing_clusters)
            
            if matched_cluster:
                issue.cluster_id = matched_cluster.id
                matched_cluster.issue_count += 1
                matched_cluster.last_seen = issue.extracted_at
            else:
                # Create new cluster (will name later in batch)
                new_cluster = IssueCluster(
                    category=category,
                    subcategory=subcategory,
                    cluster_name=f"New: {issue.summary[:50]}",  # Temp name
                    issue_count=1,
                    first_seen=issue.extracted_at,
                    last_seen=issue.extracted_at
                )
                db.add(new_cluster)
                db.flush()
                issue.cluster_id = new_cluster.id
                existing_clusters.append(new_cluster)
    
    db.commit()
    
    # Name new clusters using Claude
    unnamed_clusters = db.query(IssueCluster).filter(
        IssueCluster.cluster_name.like("New:%")
    ).all()
    
    for cluster in unnamed_clusters:
        issues = db.query(ExtractedIssue).filter(
            ExtractedIssue.cluster_id == cluster.id
        ).all()
        
        if len(issues) >= 2:  # Only name clusters with 2+ issues
            naming = name_cluster([i.__dict__ for i in issues])
            cluster.cluster_name = naming['cluster_name']
            cluster.cluster_summary = naming['cluster_summary']
    
    db.commit()


def find_matching_cluster(issue: ExtractedIssue, clusters: list) -> IssueCluster:
    """Simple keyword matching - can upgrade to embeddings later."""
    issue_words = set(issue.summary.lower().split())
    
    best_match = None
    best_score = 0
    
    for cluster in clusters:
        cluster_words = set(cluster.cluster_name.lower().split())
        overlap = len(issue_words & cluster_words)
        score = overlap / max(len(issue_words), 1)
        
        if score > 0.3 and score > best_score:
            best_match = cluster
            best_score = score
    
    return best_match


def update_cluster_trends():
    """Calculate 7-day trends for all active clusters."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    clusters = db.query(IssueCluster).filter(IssueCluster.is_active == True).all()
    
    for cluster in clusters:
        count_7d = db.query(ExtractedIssue).filter(
            ExtractedIssue.cluster_id == cluster.id,
            ExtractedIssue.extracted_at >= week_ago
        ).count()
        
        count_prior_7d = db.query(ExtractedIssue).filter(
            ExtractedIssue.cluster_id == cluster.id,
            ExtractedIssue.extracted_at >= two_weeks_ago,
            ExtractedIssue.extracted_at < week_ago
        ).count()
        
        cluster.count_7d = count_7d
        cluster.count_prior_7d = count_prior_7d
        
        if count_prior_7d > 0:
            cluster.trend_pct = ((count_7d - count_prior_7d) / count_prior_7d) * 100
        else:
            cluster.trend_pct = 100 if count_7d > 0 else 0
        
        # Update unique customer count
        cluster.unique_customers = db.query(
            func.count(func.distinct(Ticket.requester_org_name))
        ).join(ExtractedIssue).filter(
            ExtractedIssue.cluster_id == cluster.id
        ).scalar()
    
    db.commit()
```

---

## Background Jobs

```python
# Using APScheduler or similar

def daily_sync_job():
    """Run daily at 2 AM."""
    sync_tickets()  # Fetch new/updated tickets
    analyze_unprocessed_tickets()  # Run through Claude
    cluster_issues()  # Group into clusters
    update_cluster_trends()  # Recalc trends

def analyze_unprocessed_tickets():
    """Process tickets that haven't been analyzed yet."""
    unprocessed = db.query(Ticket).filter(
        Ticket.analyzed_at.is_(None)
    ).limit(500).all()  # Process in batches
    
    for ticket in unprocessed:
        try:
            result = extract_issues(ticket.__dict__)
            
            for issue_data in result.get('issues', []):
                issue = ExtractedIssue(
                    ticket_id=ticket.id,
                    category=issue_data['category'],
                    subcategory=issue_data['subcategory'],
                    issue_type=issue_data['issue_type'],
                    severity=issue_data['severity'],
                    summary=issue_data['summary'],
                    detail=issue_data.get('detail'),
                    representative_quote=issue_data.get('representative_quote'),
                    confidence=issue_data.get('confidence')
                )
                db.add(issue)
            
            ticket.analyzed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to analyze ticket {ticket.zendesk_ticket_id}: {e}")
            continue
```

---

## Frontend Components

### Dashboard Page (`/`)

```typescript
// Fetch summary stats and top clusters
// Display: 4 summary cards, trend chart, top 10 clusters table

interface DashboardData {
  summary: {
    total_issues_7d: number;
    critical_count: number;
    high_count: number;
    medium_count: number;
    by_category: { category: string; count: number }[];
  };
  trend: { week: string; count: number }[];
  top_clusters: Cluster[];
  emerging: Cluster[];  // New clusters from past 7 days
}
```

### Cluster List Page (`/clusters`)

```typescript
// Filterable, sortable table of all clusters
// Columns: Name, Category, Issues, Customers, Trend, Status, Last Seen

interface ClusterFilters {
  category?: string;
  subcategory?: string;
  is_active?: boolean;
  pm_status?: string;
  sort_by?: 'issue_count' | 'trend_pct' | 'last_seen';
  sort_order?: 'asc' | 'desc';
}
```

### Cluster Detail Page (`/clusters/[id]`)

```typescript
// Header: cluster name, summary, metrics
// Status dropdown + notes textarea (editable)
// Table of tickets with Zendesk links

interface ClusterDetail {
  cluster: Cluster;
  issues: Issue[];
  tickets: {
    zendesk_ticket_id: number;
    subject: string;
    requester_org_name: string;
    ticket_created_at: string;
    severity: string;
    zendesk_url: string;  // Constructed: https://{subdomain}.zendesk.com/agent/tickets/{id}
  }[];
}
```

### Zendesk URL Construction

```typescript
const ZENDESK_SUBDOMAIN = process.env.NEXT_PUBLIC_ZENDESK_SUBDOMAIN;

function getZendeskTicketUrl(ticketId: number): string {
  return `https://${ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/${ticketId}`;
}
```

---

## Railway Configuration

### Backend (`backend/railway.toml`)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

### Frontend (`frontend/railway.toml`)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/"
```

### Services to Create in Railway

1. **PostgreSQL** - Managed database
2. **Redis** - For background job queue (optional, can use pg-based queue)
3. **Backend** - FastAPI app
4. **Frontend** - Next.js app

---

## Implementation Order

1. **Database**: Create PostgreSQL in Railway, run migrations
2. **Zendesk client**: Auth, search, fetch tickets with comments
3. **Sync service**: Incremental sync + backfill mode
4. **Claude integration**: Extraction prompt, API calls
5. **Analysis pipeline**: Process tickets → save issues
6. **Clustering**: Group issues, name clusters, calc trends
7. **API endpoints**: Issues, clusters, export
8. **Frontend**: Dashboard, cluster list, detail pages
9. **Background jobs**: Daily sync scheduler

---

## Testing Commands

```bash
# Local dev
docker-compose up -d postgres redis
cd backend && uvicorn app.main:app --reload

# Trigger backfill (90 days)
curl -X POST http://localhost:8000/api/sync/trigger?backfill_days=90

# Check sync status
curl http://localhost:8000/api/sync/status

# Test extraction on single ticket
curl http://localhost:8000/api/debug/analyze?ticket_id=12345
```
