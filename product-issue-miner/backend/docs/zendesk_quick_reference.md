# Zendesk Client - Quick Reference

## Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=dclark@workwelltech.com
ZENDESK_API_TOKEN=your_token_here
```

## Import

```python
from app.services import (
    ZendeskClient,
    ZendeskAPIError,
    ZendeskRateLimitError,
    get_zendesk_client
)
```

## Basic Usage

```python
# Create client
client = get_zendesk_client()

# Use with context manager (recommended)
async with client:
    # Your code here
    pass
```

## Common Operations

### Search Tickets

```python
# Simple search
results = await client.search_tickets("type:ticket tags:product_issue")
tickets = results["results"]

# With pagination
results = await client.search_tickets(
    query="type:ticket status:open",
    page=2,
    per_page=50
)
```

### Get Single Ticket

```python
ticket = await client.get_ticket(12345)
print(ticket["subject"])
print(ticket["status"])
```

### Get Ticket with Comments

```python
data = await client.get_ticket_with_comments(12345)

ticket = data["ticket"]
internal_notes = data["internal_notes"]  # Staff only
public_comments = data["public_comments"]  # Customer visible
```

### Paginated Search

```python
# Auto-pagination through all results
async for batch in client.paginate_search("type:ticket"):
    for ticket in batch:
        print(f"#{ticket['id']}: {ticket['subject']}")
```

### Format Comments

```python
# Get human-readable text from comments
formatted = client.format_comments(internal_notes)
print(formatted)
```

## Search Query Examples

```python
# By tags
"type:ticket tags:product_issue"

# By status
"type:ticket status:open status:pending"

# By date
"type:ticket created>2024-01-01"
"type:ticket updated<2024-12-31"

# By priority
"type:ticket priority:high priority:urgent"

# Combined
"type:ticket tags:bug status:open created>2024-01-01"

# By custom field
"type:ticket fieldvalue:product_name"
```

## Error Handling

```python
try:
    async with client:
        ticket = await client.get_ticket(12345)
except ZendeskRateLimitError as e:
    # Rate limit exceeded after retries
    print(f"Rate limited: {e}")
    await asyncio.sleep(60)
except ZendeskAPIError as e:
    # Other API errors
    print(f"API error: {e}")
```

## Parallel Requests

```python
import asyncio

# Fetch multiple tickets in parallel
async with client:
    tasks = [
        client.get_ticket(123),
        client.get_ticket(456),
        client.get_ticket(789)
    ]
    tickets = await asyncio.gather(*tasks)
```

## Rate Limiting

```python
# Automatic - no action required!
# Client enforces 700 requests/minute

# To limit concurrency:
from asyncio import Semaphore

semaphore = Semaphore(10)  # Max 10 concurrent

async with semaphore:
    await client.get_ticket(ticket_id)
```

## Complete Example

```python
from app.services import get_zendesk_client
import asyncio

async def analyze_product_issues():
    """Fetch and analyze all product issue tickets."""
    client = get_zendesk_client()

    async with client:
        # Search for product issues
        query = "type:ticket tags:product_issue status:open"

        # Process all results with auto-pagination
        total = 0
        async for batch in client.paginate_search(query, page_size=100):
            for ticket in batch:
                # Get full details with comments
                data = await client.get_ticket_with_comments(ticket["id"])

                # Extract internal notes
                notes = data["internal_notes"]

                # Format for analysis
                notes_text = client.format_comments(notes)

                # Analyze with AI (your code)
                await analyze_with_ai(ticket["id"], notes_text)

                total += 1

        print(f"Analyzed {total} tickets")

# Run
asyncio.run(analyze_product_issues())
```

## Common Patterns

### Batch Processing with Limit

```python
from asyncio import Semaphore

async def fetch_many(ticket_ids: list, max_concurrent: int = 10):
    client = get_zendesk_client()
    semaphore = Semaphore(max_concurrent)

    async def fetch_one(tid):
        async with semaphore:
            return await client.get_ticket_with_comments(tid)

    async with client:
        results = await asyncio.gather(*[fetch_one(tid) for tid in ticket_ids])
        return results
```

### Export to File

```python
async def export_ticket(ticket_id: int, filename: str):
    client = get_zendesk_client()

    async with client:
        data = await client.get_ticket_with_comments(ticket_id)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Ticket #{ticket_id}\n")
            f.write(f"Subject: {data['ticket']['subject']}\n\n")
            f.write(client.format_comments(data["all_comments"]))
```

### Search and Filter

```python
async def find_high_priority_bugs():
    client = get_zendesk_client()

    async with client:
        results = await client.search_tickets(
            "type:ticket tags:bug priority:high status:open"
        )

        # Further filter in Python if needed
        urgent_bugs = [
            t for t in results["results"]
            if "urgent" in t.get("subject", "").lower()
        ]

        return urgent_bugs
```

## Response Structures

### Ticket Object

```python
{
    "id": 12345,
    "subject": "Issue with product",
    "description": "Full description...",
    "status": "open",  # open, pending, solved, closed
    "priority": "high",  # low, normal, high, urgent
    "tags": ["product_issue", "bug"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-16T14:20:00Z",
    "requester_id": 123,
    "assignee_id": 456,
    "organization_id": 789,
    "custom_fields": [...]
}
```

### Comment Object

```python
{
    "id": 987654321,
    "type": "Comment",
    "author_id": 123456,
    "body": "Comment text...",
    "html_body": "<p>Comment text...</p>",
    "plain_body": "Comment text...",
    "public": False,  # True = public, False = internal
    "created_at": "2024-01-15T10:30:00Z"
}
```

### Search Results

```python
{
    "results": [ticket1, ticket2, ...],
    "count": 150,  # Total results
    "next_page": "https://...?page=2" or None,
    "previous_page": "https://...?page=1" or None
}
```

### Ticket with Comments

```python
{
    "ticket": {...},
    "internal_notes": [comment1, comment2, ...],  # public=False
    "public_comments": [comment3, comment4, ...],  # public=True
    "all_comments": [comment1, comment2, comment3, ...]  # All
}
```

## Logging

```python
import logging

# Basic logging
logging.basicConfig(level=logging.INFO)

# Debug mode
logging.getLogger("app.services.zendesk").setLevel(logging.DEBUG)

# Custom format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Configuration

### Environment Variables

```bash
# Required
ZENDESK_SUBDOMAIN=workwelltech
ZENDESK_EMAIL=user@company.com
ZENDESK_API_TOKEN=your_token_here

# Optional (for other services)
ANTHROPIC_API_KEY=...
DATABASE_URL=...
```

### Settings Access

```python
from app.config import settings

print(settings.ZENDESK_SUBDOMAIN)
print(settings.zendesk_api_url)
```

## Testing

```bash
# Run test script
python test_zendesk_client.py

# Test import
python -c "from app.services import get_zendesk_client; print('OK')"
```

## Troubleshooting

### Import Error: No module named 'httpx'

```bash
pip install httpx
```

### Authentication Error (401)

Check `.env` file:
- Verify `ZENDESK_EMAIL` is correct
- Verify `ZENDESK_API_TOKEN` is valid
- Ensure `.env` is in the correct directory

### Rate Limit Error

The client handles this automatically. If you see errors:
- Reduce concurrent requests
- Add delays between batches
- Check for other processes using same token

### Empty Results

- Test query in Zendesk UI first
- Check API token permissions
- Verify ticket tags and filters

## API Limits

| Limit | Value |
|-------|-------|
| Requests per minute | 700 |
| Results per page | 100 (max) |
| Max retries | 3 |
| Initial backoff | 1 second |
| Max backoff | 60 seconds |

## File Locations

| File | Path |
|------|------|
| Client | `app/services/zendesk.py` |
| Config | `app/config.py` |
| Test | `test_zendesk_client.py` |
| Docs | `docs/zendesk_client.md` |
| Architecture | `docs/zendesk_architecture.md` |

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` with Zendesk credentials
3. Test: `python test_zendesk_client.py`
4. Integrate into your application

## Support

- Full docs: `docs/zendesk_client.md`
- Architecture: `docs/zendesk_architecture.md`
- Test script: `test_zendesk_client.py`
- Zendesk API: https://developer.zendesk.com/api-reference/
