# Zendesk Client Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  • API Endpoints (FastAPI)                                      │
│  • Background Tasks (APScheduler)                               │
│  • Database Operations (SQLAlchemy)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ uses
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  get_zendesk_client()                           │
│                   Factory Function                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ creates
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   ZendeskClient                                 │
├─────────────────────────────────────────────────────────────────┤
│  Core Methods:                                                  │
│  • search_tickets()                                             │
│  • get_ticket()                                                 │
│  • get_ticket_comments()                                        │
│  • get_ticket_with_comments()                                   │
│  • paginate_search()                                            │
│  • format_comments()                                            │
├─────────────────────────────────────────────────────────────────┤
│  Internal Features:                                             │
│  • Rate Limiting (_check_rate_limit)                            │
│  • Error Handling (_request with retry)                         │
│  • HTTP Client Management (httpx.AsyncClient)                   │
│  • Authentication (Basic Auth header)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ uses
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   httpx.AsyncClient                             │
├─────────────────────────────────────────────────────────────────┤
│  • Async HTTP requests                                          │
│  • Connection pooling                                           │
│  • Timeout handling                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP requests
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              Zendesk API (api.zendesk.com)                      │
├─────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                     │
│  • GET /api/v2/search.json                                      │
│  • GET /api/v2/tickets/{id}.json                                │
│  • GET /api/v2/tickets/{id}/comments.json                       │
│  • GET /api/v2/users/{id}.json                                  │
│  • GET /api/v2/organizations/{id}.json                          │
└─────────────────────────────────────────────────────────────────┘
```

## Request Flow

```
User/Application
      │
      │ 1. Call method
      ▼
ZendeskClient.search_tickets(query)
      │
      │ 2. Check rate limit
      ▼
_check_rate_limit()
      │
      │ 3. Make HTTP request with retry
      ▼
_request(method, endpoint)
      │
      ├─── Retry on 429 (rate limit)
      ├─── Retry on 5xx (server error)
      ├─── Exponential backoff
      └─── Max 3 retries
      │
      │ 4. HTTP request
      ▼
httpx.AsyncClient.request()
      │
      │ 5. HTTP/HTTPS
      ▼
Zendesk API (workwelltech.zendesk.com)
      │
      │ 6. JSON response
      ▼
ZendeskClient
      │
      │ 7. Return data
      ▼
Application
```

## Rate Limiting Flow

```
Request arrives
      │
      ▼
Acquire rate_limit_lock
      │
      ▼
Check current window
      │
      ├─── Window expired (>60s)?
      │    │
      │    └──▶ Reset counter to 0
      │         Reset window start time
      │
      ▼
Check request count
      │
      ├─── Count >= 700?
      │    │
      │    └──▶ Calculate sleep time
      │         Sleep (60 - elapsed)
      │         Reset counter to 0
      │
      ▼
Increment request count
      │
      ▼
Release lock
      │
      ▼
Proceed with request
```

## Error Handling Flow

```
_request() called
      │
      ▼
Try HTTP request
      │
      ├─── 429 (Rate Limit)
      │    │
      │    ├──▶ Read Retry-After header
      │    │    Sleep (Retry-After seconds)
      │    │    Increment retry counter
      │    │
      │    └──▶ Retry < MAX_RETRIES?
      │         ├─ Yes: Retry request
      │         └─ No: Raise ZendeskRateLimitError
      │
      ├─── 5xx (Server Error)
      │    │
      │    ├──▶ Log error
      │    │    Sleep (exponential backoff)
      │    │    Increment retry counter
      │    │
      │    └──▶ Retry < MAX_RETRIES?
      │         ├─ Yes: Retry request
      │         └─ No: Raise ZendeskAPIError
      │
      ├─── 4xx (Client Error)
      │    │
      │    └──▶ Raise ZendeskAPIError
      │         (no retry)
      │
      ├─── Network Error
      │    │
      │    ├──▶ Log error
      │    │    Sleep (exponential backoff)
      │    │    Increment retry counter
      │    │
      │    └──▶ Retry < MAX_RETRIES?
      │         ├─ Yes: Retry request
      │         └─ No: Raise ZendeskAPIError
      │
      └─── Success (2xx)
           │
           └──▶ Return JSON response
```

## Pagination Flow

### Manual Pagination (search_tickets)

```
search_tickets(query, page=1)
      │
      ▼
Make request to /search.json?page=1
      │
      ▼
Return response:
  {
    "results": [tickets],
    "next_page": "url",
    "count": total
  }
      │
      ▼
User manually fetches next page
```

### Auto Pagination (paginate_search)

```
paginate_search(query) → AsyncGenerator
      │
      │ Initial: page = 1
      ▼
┌─▶ search_tickets(query, page)
│     │
│     ▼
│   Get response
│     │
│     ├─── results empty?
│     │    └──▶ STOP (no more results)
│     │
│     ▼
│   Yield batch of tickets
│     │
│     ▼
│   Check next_page
│     │
│     ├─── next_page exists?
│     │    │
│     │    ├─ Yes: page += 1
│     │    │       Continue loop ─┐
│     │    │                      │
│     │    └─ No: STOP           │
│     │                           │
└─────┴───────────────────────────┘
```

## Comment Separation Flow

```
get_ticket_with_comments(ticket_id)
      │
      ├─────────────────┬─────────────────┐
      │                 │                 │
      │ Parallel:       │                 │
      │                 │                 │
      ▼                 ▼                 │
get_ticket()    get_ticket_comments()    │
      │                 │                 │
      └─────────┬───────┘                 │
                │                         │
                ▼                         │
        await asyncio.gather()            │
                │                         │
                ▼                         │
        ticket, comments = results        │
                │                         │
                ▼                         │
        Separate by public field:         │
                │                         │
                ├──▶ internal_notes       │
                │    (public = False)     │
                │                         │
                ├──▶ public_comments      │
                │    (public = True)      │
                │                         │
                └──▶ all_comments         │
                     (chronological)      │
                │                         │
                ▼                         │
        Return dict:                      │
          {                               │
            "ticket": {...},              │
            "internal_notes": [...],      │
            "public_comments": [...],     │
            "all_comments": [...]         │
          }                               │
```

## Authentication Flow

```
Client Initialization
      │
      ▼
credentials = f"{email}/token:{api_token}"
      │
      ▼
auth_header = base64.b64encode(credentials)
      │
      ▼
Create httpx.AsyncClient with headers:
  {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/json",
    "Accept": "application/json"
  }
      │
      ▼
Every request includes Authorization header
      │
      ▼
Zendesk validates credentials
```

## Data Flow Example: Search and Analyze

```
Application needs to analyze product issues
      │
      ▼
1. Search for tickets
   query = "type:ticket tags:product_issue"
      │
      ▼
2. Paginate through results
   async for batch in paginate_search(query):
      │
      ▼
3. For each ticket in batch:
      │
      ├──▶ get_ticket_with_comments(ticket_id)
      │         │
      │         ▼
      │    Parallel fetch:
      │      • Ticket details
      │      • All comments
      │         │
      │         ▼
      │    Separate comments:
      │      • Internal notes
      │      • Public comments
      │         │
      │         ▼
      │    Return combined data
      │
      ▼
4. Format internal notes
   format_comments(internal_notes)
      │
      ▼
5. Send to AI for analysis
   analyze_with_claude(formatted_text)
      │
      ▼
6. Store results in database
   save_analysis_to_db(analysis)
```

## Concurrency Model

```
Application Layer
      │
      │ Creates multiple tasks
      │
      ├──────┬──────┬──────┬──────┐
      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼
   Task 1  Task 2  Task 3  Task 4  Task 5
      │      │      │      │      │
      │      │      │      │      │
      └──────┴───┬──┴──────┴──────┘
                 │
                 ▼
          Shared ZendeskClient
                 │
                 ├──▶ Rate Limit Lock (asyncio.Lock)
                 │    Ensures sequential rate checking
                 │
                 ▼
          httpx.AsyncClient
                 │
                 ├──▶ Connection Pool
                 │    Reuses HTTP connections
                 │
                 ▼
          Concurrent HTTP requests
                 │
                 ▼
          Zendesk API
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  API Endpoints   │      │  Background Jobs │           │
│  │                  │      │                  │           │
│  │  POST /analyze   │      │  Scheduled Sync  │           │
│  │  GET /tickets    │      │  Daily Analysis  │           │
│  └────────┬─────────┘      └────────┬─────────┘           │
│           │                         │                      │
│           │                         │                      │
│           ▼                         ▼                      │
│  ┌────────────────────────────────────────────┐           │
│  │         ZendeskClient                      │           │
│  │                                            │           │
│  │  • Fetch tickets                           │           │
│  │  • Get comments                            │           │
│  │  • Separate internal/public                │           │
│  └────────┬────────────────────┬──────────────┘           │
│           │                    │                          │
│           ▼                    ▼                          │
│  ┌────────────────┐   ┌────────────────┐                 │
│  │  AI Analyzer   │   │   Database     │                 │
│  │                │   │                │                 │
│  │  Claude API    │   │  PostgreSQL    │                 │
│  │  Issue Mining  │   │  Store Results │                 │
│  └────────────────┘   └────────────────┘                 │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## Configuration Flow

```
Application Startup
      │
      ▼
Load .env file
      │
      ▼
Create Settings instance
  (pydantic-settings)
      │
      ▼
Validate configuration:
  • ZENDESK_SUBDOMAIN
  • ZENDESK_EMAIL
  • ZENDESK_API_TOKEN
      │
      ▼
get_zendesk_client() factory
      │
      ▼
Create ZendeskClient(
  subdomain=settings.ZENDESK_SUBDOMAIN,
  email=settings.ZENDESK_EMAIL,
  api_token=settings.ZENDESK_API_TOKEN
)
      │
      ▼
Ready to use
```

## File Structure

```
product-issue-miner/backend/
│
├── app/
│   ├── services/
│   │   ├── __init__.py          # Exports client
│   │   └── zendesk.py           # ★ Main client
│   │
│   └── config.py                # Settings (ZENDESK_*)
│
├── docs/
│   ├── zendesk_client.md        # Full documentation
│   └── zendesk_architecture.md  # ★ This file
│
├── test_zendesk_client.py       # Test script
├── ZENDESK_CLIENT_SUMMARY.md    # Implementation summary
└── requirements.txt             # httpx dependency
```

## Class Hierarchy

```
ZendeskClient
  │
  ├─ Properties:
  │   ├─ base_url: str
  │   ├─ auth_header: str
  │   ├─ _client: httpx.AsyncClient
  │   ├─ _request_count: int
  │   ├─ _rate_limit_window_start: datetime
  │   └─ _rate_limit_lock: asyncio.Lock
  │
  ├─ Public Methods:
  │   ├─ search_tickets()
  │   ├─ get_ticket()
  │   ├─ get_ticket_comments()
  │   ├─ get_ticket_with_comments()
  │   ├─ paginate_search()
  │   ├─ format_comments()
  │   ├─ get_user()
  │   ├─ get_organization()
  │   └─ close()
  │
  ├─ Private Methods:
  │   ├─ _ensure_client()
  │   ├─ _check_rate_limit()
  │   └─ _request()
  │
  └─ Magic Methods:
      ├─ __init__()
      ├─ __aenter__()
      └─ __aexit__()

Exceptions:
  ├─ ZendeskAPIError
  └─ ZendeskRateLimitError

Factory:
  └─ get_zendesk_client() → ZendeskClient
```
