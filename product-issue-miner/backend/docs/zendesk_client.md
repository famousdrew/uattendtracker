# Zendesk API Client Documentation

## Overview

The `ZendeskClient` provides a robust, production-ready async client for interacting with the Zendesk API v2. It includes comprehensive error handling, rate limiting, automatic retries, and pagination support.

## Features

- **Async/Await Support**: Built on `httpx` AsyncClient for efficient concurrent operations
- **Rate Limiting**: Automatic enforcement of Zendesk's 700 requests/minute limit
- **Error Handling**: Exponential backoff retry for 429 (rate limit) and 5xx errors
- **Pagination**: Automatic pagination for search results and comments
- **Comment Separation**: Automatic separation of internal notes from public comments
- **Context Manager**: Support for async context manager pattern
- **Type Hints**: Full type annotations for better IDE support

## Installation

Required dependencies (already in requirements.txt):
```
httpx==0.26.0
```

## Quick Start

```python
from app.services import get_zendesk_client

async def main():
    # Create client using factory function
    client = get_zendesk_client()

    # Use as async context manager (recommended)
    async with client:
        # Search for tickets
        results = await client.search_tickets("type:ticket tags:product_issue")
        tickets = results["results"]

        # Get a specific ticket with comments
        data = await client.get_ticket_with_comments(12345)
        ticket = data["ticket"]
        internal_notes = data["internal_notes"]
```

## Authentication

The client uses Zendesk API token authentication (Basic Auth):

```python
# Authentication format: email/token:api_token
# Base64 encoded and sent as Authorization header

ZendeskClient(
    subdomain="workwelltech",  # company.zendesk.com
    email="user@company.com",
    api_token="your_api_token_here"
)
```

Configuration is loaded from environment variables via `app.config.Settings`:
- `ZENDESK_SUBDOMAIN`: Company subdomain (default: "workwelltech")
- `ZENDESK_EMAIL`: Email for API authentication
- `ZENDESK_API_TOKEN`: API token from Zendesk

## Core Methods

### Search Tickets

```python
async def search_tickets(query: str, page: int = 1, per_page: int = 100) -> dict
```

Search tickets using Zendesk search syntax.

**Parameters:**
- `query`: Zendesk search query (e.g., `"type:ticket status:open"`)
- `page`: Page number (1-indexed)
- `per_page`: Results per page (max 100)

**Returns:**
```python
{
    "results": [...],      # List of ticket objects
    "count": 150,          # Total results
    "next_page": "...",    # URL for next page (or None)
    "previous_page": "..." # URL for previous page (or None)
}
```

**Example:**
```python
results = await client.search_tickets(
    query="type:ticket tags:product_issue created>2024-01-01",
    per_page=50
)

for ticket in results["results"]:
    print(f"Ticket #{ticket['id']}: {ticket['subject']}")
```

**Common Search Queries:**
```python
# By tags
"type:ticket tags:product_issue"

# By status
"type:ticket status:open status:pending"

# By date range
"type:ticket created>2024-01-01 created<2024-12-31"

# Combined filters
"type:ticket tags:bug status:open priority:high"

# By custom field
"type:ticket fieldvalue:product_name"
```

### Get Single Ticket

```python
async def get_ticket(ticket_id: int) -> dict
```

Fetch a single ticket by ID.

**Parameters:**
- `ticket_id`: Zendesk ticket ID

**Returns:** Ticket object dictionary

**Example:**
```python
ticket = await client.get_ticket(12345)
print(f"Subject: {ticket['subject']}")
print(f"Status: {ticket['status']}")
print(f"Priority: {ticket['priority']}")
```

### Get Ticket Comments

```python
async def get_ticket_comments(ticket_id: int) -> list
```

Fetch all comments for a ticket (including internal notes). Automatically handles pagination.

**Parameters:**
- `ticket_id`: Zendesk ticket ID

**Returns:** List of comment objects

**Comment Object Structure:**
```python
{
    "id": 123456789,
    "type": "Comment",
    "author_id": 123456,
    "body": "Comment text...",
    "html_body": "<p>Comment text...</p>",
    "plain_body": "Comment text...",
    "public": False,  # True = public, False = internal note
    "created_at": "2024-01-15T10:30:00Z"
}
```

**Example:**
```python
comments = await client.get_ticket_comments(12345)

# Separate internal from public
internal = [c for c in comments if not c["public"]]
public = [c for c in comments if c["public"]]

print(f"Internal notes: {len(internal)}")
print(f"Public comments: {len(public)}")
```

### Get Ticket With Comments

```python
async def get_ticket_with_comments(ticket_id: int) -> dict
```

Fetch ticket and comments in parallel, with automatic separation of internal/public comments.

**Parameters:**
- `ticket_id`: Zendesk ticket ID

**Returns:**
```python
{
    "ticket": {...},           # Ticket object
    "internal_notes": [...],   # Comments where public=False
    "public_comments": [...],  # Comments where public=True
    "all_comments": [...]      # All comments chronologically
}
```

**Example:**
```python
data = await client.get_ticket_with_comments(12345)

ticket = data["ticket"]
print(f"Ticket: {ticket['subject']}")

# Process internal notes
for note in data["internal_notes"]:
    print(f"Internal: {note['plain_body']}")
```

### Paginated Search

```python
async def paginate_search(query: str, page_size: int = 100) -> AsyncGenerator
```

Generator that automatically handles pagination for large result sets.

**Parameters:**
- `query`: Zendesk search query
- `page_size`: Results per page (max 100)

**Yields:** Lists of ticket objects (batches)

**Example:**
```python
total = 0
async for batch in client.paginate_search("type:ticket tags:product_issue"):
    total += len(batch)
    print(f"Processing batch of {len(batch)} tickets...")

    for ticket in batch:
        # Process each ticket
        pass

print(f"Processed {total} total tickets")
```

### Format Comments

```python
def format_comments(comments: list) -> str
```

Format a list of comments into a readable text string.

**Parameters:**
- `comments`: List of comment objects

**Returns:** Formatted multi-line string

**Example:**
```python
data = await client.get_ticket_with_comments(12345)
formatted = client.format_comments(data["internal_notes"])

# Output:
# --- Comment 1 (Internal Note) ---
# Author ID: 123456
# Created: 2024-01-15 10:30:00 UTC
#
# This is the comment text...
#
# --- Comment 2 (Internal Note) ---
# ...
```

### Get User

```python
async def get_user(user_id: int) -> dict
```

Fetch user information by ID.

**Example:**
```python
user = await client.get_user(123456)
print(f"Name: {user['name']}")
print(f"Email: {user['email']}")
```

### Get Organization

```python
async def get_organization(org_id: int) -> dict
```

Fetch organization information by ID.

**Example:**
```python
org = await client.get_organization(789)
print(f"Organization: {org['name']}")
```

## Rate Limiting

The client automatically enforces Zendesk's 700 requests/minute rate limit:

- Tracks requests per minute window
- Automatically sleeps when limit would be exceeded
- Resets counter every 60 seconds
- Respects `Retry-After` header on 429 responses

**Implementation:**
```python
# Automatic rate limiting
async with self._rate_limit_lock:
    if self._request_count >= 700:
        sleep_time = 60 - elapsed_seconds
        await asyncio.sleep(sleep_time)
        self._request_count = 0
```

## Error Handling

The client includes comprehensive error handling with automatic retries:

### Rate Limit Errors (429)

- Automatically retries up to 3 times
- Respects `Retry-After` header
- Raises `ZendeskRateLimitError` after max retries

### Server Errors (5xx)

- Automatically retries up to 3 times
- Exponential backoff: 1s, 2s, 4s, ... (max 60s)
- Raises `ZendeskAPIError` after max retries

### Client Errors (4xx except 429)

- No retry (client error, won't succeed on retry)
- Raises `ZendeskAPIError` immediately

### Network Errors

- Retries up to 3 times with exponential backoff
- Raises `ZendeskAPIError` after max retries

**Example:**
```python
from app.services import ZendeskAPIError, ZendeskRateLimitError

try:
    ticket = await client.get_ticket(12345)
except ZendeskRateLimitError as e:
    # Rate limit exceeded even after retries
    logger.error(f"Rate limit error: {e}")
except ZendeskAPIError as e:
    # Other API errors
    logger.error(f"API error: {e}")
```

## Best Practices

### 1. Use Context Manager

Always use async context manager to ensure proper cleanup:

```python
async with get_zendesk_client() as client:
    # Use client
    pass
# Client automatically closed
```

### 2. Batch Operations

Use `paginate_search()` for large result sets:

```python
async for batch in client.paginate_search(query, page_size=100):
    # Process batch
    await process_batch(batch)
```

### 3. Parallel Requests

Use `asyncio.gather()` for independent requests:

```python
# Fetch multiple tickets in parallel
tickets = await asyncio.gather(
    client.get_ticket(123),
    client.get_ticket(456),
    client.get_ticket(789)
)
```

### 4. Error Handling

Always handle exceptions appropriately:

```python
try:
    async with client:
        results = await client.search_tickets(query)
except ZendeskRateLimitError:
    # Handle rate limiting
    await asyncio.sleep(60)
    retry()
except ZendeskAPIError as e:
    # Handle other errors
    logger.error(f"API error: {e}")
```

### 5. Logging

The client includes comprehensive logging. Configure logging level:

```python
import logging

logging.basicConfig(level=logging.INFO)
# Or for debugging:
logging.getLogger("app.services.zendesk").setLevel(logging.DEBUG)
```

## Common Patterns

### Search and Process All Tickets

```python
async def process_all_product_issues():
    client = get_zendesk_client()

    async with client:
        query = "type:ticket tags:product_issue status:open"

        async for batch in client.paginate_search(query):
            for ticket in batch:
                # Get full details with comments
                data = await client.get_ticket_with_comments(ticket["id"])

                # Process internal notes
                for note in data["internal_notes"]:
                    await analyze_note(note)
```

### Bulk Fetch with Concurrency Limit

```python
import asyncio
from asyncio import Semaphore

async def fetch_tickets_with_limit(ticket_ids: list, max_concurrent: int = 10):
    client = get_zendesk_client()
    semaphore = Semaphore(max_concurrent)

    async def fetch_one(ticket_id):
        async with semaphore:
            return await client.get_ticket_with_comments(ticket_id)

    async with client:
        results = await asyncio.gather(
            *[fetch_one(tid) for tid in ticket_ids]
        )

    return results
```

### Export Comments to Text

```python
async def export_ticket_notes(ticket_id: int, output_file: str):
    client = get_zendesk_client()

    async with client:
        data = await client.get_ticket_with_comments(ticket_id)

        # Format all comments
        all_text = client.format_comments(data["all_comments"])

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Ticket #{ticket_id}: {data['ticket']['subject']}\n\n")
            f.write(all_text)
```

## Testing

Run the test script to verify configuration:

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
python test_zendesk_client.py
```

The test script includes:
- Basic search functionality
- Ticket retrieval with comments
- Paginated search
- Comment formatting

## Troubleshooting

### Authentication Errors

```
HTTP 401: Couldn't authenticate you
```

**Solution:** Verify credentials in `.env`:
```
ZENDESK_EMAIL=your.email@company.com
ZENDESK_API_TOKEN=your_token_here
```

### Rate Limit Errors

```
ZendeskRateLimitError: Rate limit exceeded after 3 retries
```

**Solution:** The client automatically handles rate limiting. If you see this error:
- Reduce concurrency (fewer parallel requests)
- Increase delays between batches
- Check for other processes using the same API token

### Network Timeouts

```
Request failed after 3 retries
```

**Solution:**
- Check network connectivity
- Verify Zendesk subdomain is correct
- Increase timeout in client initialization

### Empty Results

If searches return no results:
- Verify query syntax using Zendesk's search UI first
- Check ticket permissions (API token must have access)
- Use `logger.setLevel(logging.DEBUG)` to see actual API responses

## API Reference

### Zendesk API Documentation

- [Zendesk API v2 Documentation](https://developer.zendesk.com/api-reference/)
- [Search API](https://developer.zendesk.com/api-reference/ticketing/ticket-management/search/)
- [Tickets API](https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/)
- [Ticket Comments API](https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_comments/)

### Client Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `subdomain` | str | Yes | - | Zendesk subdomain |
| `email` | str | Yes | - | Email for authentication |
| `api_token` | str | Yes | - | API token |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `RATE_LIMIT` | 700 | Requests per minute |
| `MAX_RETRIES` | 3 | Maximum retry attempts |
| `INITIAL_BACKOFF` | 1 | Initial backoff seconds |
| `MAX_BACKOFF` | 60 | Maximum backoff seconds |

## License

Part of the Product Issue Miner application.
