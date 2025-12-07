# Zendesk API Client - Implementation Summary

## Files Created

### 1. Core Client: `app/services/zendesk.py`

**Location:** `C:\dev\uattendissuetrack\product-issue-miner\backend\app\services\zendesk.py`

**Classes:**
- `ZendeskClient`: Main async client for Zendesk API
- `ZendeskAPIError`: Exception for API errors
- `ZendeskRateLimitError`: Exception for rate limit errors

**Key Features:**
- Async/await support using httpx AsyncClient
- Automatic rate limiting (700 requests/minute)
- Exponential backoff retry logic
- Automatic pagination handling
- Comment separation (internal vs public)
- Context manager support

**Main Methods:**
```python
# Search and retrieval
async def search_tickets(query, page, per_page) -> dict
async def get_ticket(ticket_id) -> dict
async def get_ticket_comments(ticket_id) -> list
async def get_ticket_with_comments(ticket_id) -> dict

# Pagination
async def paginate_search(query, page_size) -> AsyncGenerator

# Formatting
def format_comments(comments) -> str

# Additional
async def get_user(user_id) -> dict
async def get_organization(org_id) -> dict
```

**Factory Function:**
```python
def get_zendesk_client() -> ZendeskClient
```

### 2. Service Exports: `app/services/__init__.py`

**Location:** `C:\dev\uattendissuetrack\product-issue-miner\backend\app\services\__init__.py`

Updated to export:
- `ZendeskClient`
- `ZendeskAPIError`
- `ZendeskRateLimitError`
- `get_zendesk_client`

### 3. Test Script: `test_zendesk_client.py`

**Location:** `C:\dev\uattendissuetrack\product-issue-miner\backend\test_zendesk_client.py`

Demonstrates:
- Basic ticket search
- Fetching tickets with comments
- Paginated search
- Comment formatting

### 4. Documentation: `docs/zendesk_client.md`

**Location:** `C:\dev\uattendissuetrack\product-issue-miner\backend\docs\zendesk_client.md`

Complete documentation including:
- API reference
- Usage examples
- Best practices
- Common patterns
- Troubleshooting guide

## Implementation Details

### Authentication

Uses Zendesk API token authentication (Basic Auth):
```
Authorization: Basic base64(email/token:api_token)
```

Credentials loaded from `app.config.Settings`:
- `ZENDESK_SUBDOMAIN`: Company subdomain (default: "workwelltech")
- `ZENDESK_EMAIL`: Email for authentication
- `ZENDESK_API_TOKEN`: API token

### Rate Limiting

- **Limit:** 700 requests per minute
- **Tracking:** Per-minute window with request counter
- **Enforcement:** Automatic sleep when limit approached
- **Retry-After:** Respects header on 429 responses

Implementation:
```python
async with self._rate_limit_lock:
    if self._request_count >= 700:
        sleep_time = 60 - window_elapsed
        await asyncio.sleep(sleep_time)
```

### Error Handling

**429 Rate Limit:**
- Retry up to 3 times
- Respect Retry-After header
- Raise `ZendeskRateLimitError` after max retries

**5xx Server Errors:**
- Retry up to 3 times
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s (max 60s)
- Raise `ZendeskAPIError` after max retries

**4xx Client Errors:**
- No retry (won't succeed)
- Raise `ZendeskAPIError` immediately

**Network Errors:**
- Retry up to 3 times with exponential backoff
- Raise `ZendeskAPIError` after max retries

### Comment Separation

Comments have a `public` boolean field:
- `public: True` → Public comment (visible to customers)
- `public: False` → Internal note (staff only)

The `get_ticket_with_comments()` method automatically separates:
```python
{
    "ticket": {...},
    "internal_notes": [comments where public=False],
    "public_comments": [comments where public=True],
    "all_comments": [all comments chronologically]
}
```

### Pagination

**Search Results:**
```python
# Single page
results = await client.search_tickets(query, page=1, per_page=100)

# Auto-pagination
async for batch in client.paginate_search(query, page_size=100):
    # Process batch
```

**Comments:**
```python
# Automatically handles pagination
comments = await client.get_ticket_comments(ticket_id)
```

## Usage Examples

### Basic Search

```python
from app.services import get_zendesk_client

async def search_product_issues():
    client = get_zendesk_client()

    async with client:
        results = await client.search_tickets(
            query="type:ticket tags:product_issue status:open",
            per_page=100
        )

        for ticket in results["results"]:
            print(f"#{ticket['id']}: {ticket['subject']}")
```

### Get Ticket with Comments

```python
async def analyze_ticket(ticket_id: int):
    client = get_zendesk_client()

    async with client:
        data = await client.get_ticket_with_comments(ticket_id)

        ticket = data["ticket"]
        internal_notes = data["internal_notes"]

        print(f"Ticket: {ticket['subject']}")
        print(f"Internal notes: {len(internal_notes)}")

        # Format notes for display
        formatted = client.format_comments(internal_notes)
        print(formatted)
```

### Paginated Processing

```python
async def process_all_tickets():
    client = get_zendesk_client()

    async with client:
        total = 0

        async for batch in client.paginate_search(
            query="type:ticket tags:product_issue",
            page_size=100
        ):
            total += len(batch)

            for ticket in batch:
                await process_ticket(ticket)

        print(f"Processed {total} tickets")
```

### Parallel Fetching

```python
import asyncio

async def fetch_multiple_tickets(ticket_ids: list):
    client = get_zendesk_client()

    async with client:
        # Fetch all tickets in parallel
        tasks = [
            client.get_ticket_with_comments(tid)
            for tid in ticket_ids
        ]

        results = await asyncio.gather(*tasks)
        return results
```

## Configuration

### Environment Variables

Required in `.env` file:
```env
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=dclark@workwelltech.com
ZENDESK_API_TOKEN=your_token_here
```

### Settings Class

Loaded via `app.config.Settings`:
```python
from app.config import settings

print(settings.ZENDESK_SUBDOMAIN)  # "workwelltech"
print(settings.zendesk_api_url)    # "https://workwelltech.zendesk.com/api/v2"
```

## Testing

### Install Dependencies

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
pip install -r requirements.txt
```

### Run Test Script

```bash
python test_zendesk_client.py
```

### Import Test

```python
from app.services import (
    ZendeskClient,
    ZendeskAPIError,
    ZendeskRateLimitError,
    get_zendesk_client
)

# Should import without errors
```

## Integration Points

### Database Integration

The client is designed to work with the database models:

```python
from app.models import Ticket
from app.services import get_zendesk_client

async def sync_ticket(ticket_id: int):
    client = get_zendesk_client()

    async with client:
        data = await client.get_ticket_with_comments(ticket_id)

        # Create/update database record
        ticket = Ticket(
            zendesk_id=data["ticket"]["id"],
            subject=data["ticket"]["subject"],
            status=data["ticket"]["status"],
            # ... other fields
        )
```

### AI Analysis Integration

Comments can be formatted for AI analysis:

```python
async def prepare_for_analysis(ticket_id: int):
    client = get_zendesk_client()

    async with client:
        data = await client.get_ticket_with_comments(ticket_id)

        # Format internal notes for AI
        notes_text = client.format_comments(data["internal_notes"])

        # Send to Claude for analysis
        analysis = await analyze_with_claude(notes_text)
        return analysis
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/search.json` | GET | Search tickets |
| `/tickets/{id}.json` | GET | Get single ticket |
| `/tickets/{id}/comments.json` | GET | Get ticket comments |
| `/users/{id}.json` | GET | Get user info |
| `/organizations/{id}.json` | GET | Get organization info |

## Dependencies

From `requirements.txt`:
```
httpx==0.26.0  # Async HTTP client
```

Already installed:
```
pydantic==2.5.3           # Settings validation
pydantic-settings==2.1.0  # Environment config
python-dotenv==1.0.0      # .env file support
```

## Logging

The client uses Python's `logging` module:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set Zendesk client to DEBUG for detailed logs
logging.getLogger("app.services.zendesk").setLevel(logging.DEBUG)
```

**Log Messages:**
- `INFO`: Search results, ticket fetches, pagination progress
- `WARNING`: Rate limit warnings, retries
- `ERROR`: API errors, request failures

## Best Practices

1. **Always use context manager:**
   ```python
   async with get_zendesk_client() as client:
       # Use client
   ```

2. **Handle exceptions:**
   ```python
   try:
       ticket = await client.get_ticket(id)
   except ZendeskAPIError as e:
       logger.error(f"Failed to fetch ticket: {e}")
   ```

3. **Use pagination for large datasets:**
   ```python
   async for batch in client.paginate_search(query):
       await process_batch(batch)
   ```

4. **Limit concurrency:**
   ```python
   semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
   async with semaphore:
       await client.get_ticket(id)
   ```

5. **Log important operations:**
   ```python
   logger.info(f"Processing ticket {ticket_id}")
   ```

## Next Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Set `ZENDESK_API_TOKEN` in `.env`
   - Verify `ZENDESK_EMAIL` and `ZENDESK_SUBDOMAIN`

3. **Test the client:**
   ```bash
   python test_zendesk_client.py
   ```

4. **Integrate with application:**
   - Use in API endpoints
   - Connect to database models
   - Integrate with AI analysis service

## Support

For questions or issues:
- See full documentation: `docs/zendesk_client.md`
- Zendesk API docs: https://developer.zendesk.com/api-reference/
- Test script: `test_zendesk_client.py`
