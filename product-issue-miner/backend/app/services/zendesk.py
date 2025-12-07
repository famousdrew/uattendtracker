"""
Zendesk API client with rate limiting, error handling, and pagination support.

This module provides an async client for interacting with the Zendesk API,
including ticket search, retrieval, and comment fetching with proper
separation of internal notes and public comments.
"""

import httpx
import base64
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ZendeskRateLimitError(Exception):
    """Raised when rate limit is exceeded and cannot be retried."""
    pass


class ZendeskAPIError(Exception):
    """Raised when Zendesk API returns an error."""
    pass


class ZendeskClient:
    """Async client for Zendesk API with rate limiting and error handling."""

    BASE_URL_TEMPLATE = "https://{subdomain}.zendesk.com/api/v2"
    RATE_LIMIT = 700  # requests per minute
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 60  # seconds

    def __init__(self, subdomain: str, email: str, api_token: str):
        """
        Initialize Zendesk client.

        Args:
            subdomain: Zendesk subdomain (e.g., 'company' for company.zendesk.com)
            email: Email address for API authentication
            api_token: API token for authentication
        """
        self.base_url = self.BASE_URL_TEMPLATE.format(subdomain=subdomain)
        # Basic auth format: email/token:api_token
        credentials = f"{email}/token:{api_token}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()

        # Rate limiting tracking
        self._request_count = 0
        self._rate_limit_window_start = datetime.now()
        self._rate_limit_lock = asyncio.Lock()

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Basic {self.auth_header}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )

    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _check_rate_limit(self):
        """
        Check and enforce rate limiting.

        Tracks requests per minute and sleeps if limit would be exceeded.
        """
        async with self._rate_limit_lock:
            now = datetime.now()
            window_elapsed = (now - self._rate_limit_window_start).total_seconds()

            # Reset counter if window has passed
            if window_elapsed >= 60:
                self._request_count = 0
                self._rate_limit_window_start = now
                return

            # Check if we're approaching the limit
            if self._request_count >= self.RATE_LIMIT:
                # Calculate how long to sleep
                sleep_time = 60 - window_elapsed
                if sleep_time > 0:
                    logger.warning(
                        f"Rate limit reached ({self.RATE_LIMIT} req/min). "
                        f"Sleeping for {sleep_time:.2f} seconds"
                    )
                    await asyncio.sleep(sleep_time)

                # Reset counter after sleeping
                self._request_count = 0
                self._rate_limit_window_start = datetime.now()

            self._request_count += 1

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/tickets/123.json')
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            JSON response as dictionary

        Raises:
            ZendeskAPIError: On API errors after retries exhausted
            ZendeskRateLimitError: On rate limit errors that cannot be retried
        """
        await self._ensure_client()

        url = f"{self.base_url}{endpoint}"
        retries = 0
        backoff = self.INITIAL_BACKOFF

        while retries <= self.MAX_RETRIES:
            try:
                # Check rate limit before making request
                await self._check_rate_limit()

                # Make request
                response = await self._client.request(method, url, **kwargs)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    logger.warning(
                        f"Rate limited on {endpoint}. "
                        f"Retry after {retry_after} seconds"
                    )

                    if retries >= self.MAX_RETRIES:
                        raise ZendeskRateLimitError(
                            f"Rate limit exceeded after {retries} retries"
                        )

                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue

                # Handle server errors with retry
                if 500 <= response.status_code < 600:
                    logger.error(
                        f"Server error {response.status_code} on {endpoint}. "
                        f"Retry {retries}/{self.MAX_RETRIES}"
                    )

                    if retries >= self.MAX_RETRIES:
                        raise ZendeskAPIError(
                            f"Server error {response.status_code} after "
                            f"{retries} retries: {response.text}"
                        )

                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff = min(backoff * 2, self.MAX_BACKOFF)
                    continue

                # Raise on client errors (4xx except 429)
                response.raise_for_status()

                # Return JSON response
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error {e.response.status_code} on {endpoint}: "
                    f"{e.response.text}"
                )
                raise ZendeskAPIError(
                    f"HTTP {e.response.status_code}: {e.response.text}"
                ) from e

            except httpx.RequestError as e:
                logger.error(f"Request error on {endpoint}: {e}")

                if retries >= self.MAX_RETRIES:
                    raise ZendeskAPIError(
                        f"Request failed after {retries} retries: {e}"
                    ) from e

                await asyncio.sleep(backoff)
                retries += 1
                backoff = min(backoff * 2, self.MAX_BACKOFF)
                continue

        raise ZendeskAPIError(f"Request failed after {self.MAX_RETRIES} retries")

    async def search_tickets(
        self,
        query: str,
        page: int = 1,
        per_page: int = 100
    ) -> Dict[str, Any]:
        """
        Search tickets with pagination.

        Args:
            query: Zendesk search query (e.g., 'type:ticket status:open')
            page: Page number (1-indexed)
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing:
                - results: List of ticket objects
                - count: Total number of results
                - next_page: URL for next page (or None)
                - previous_page: URL for previous page (or None)

        Example:
            >>> results = await client.search_tickets('type:ticket tag:product_issue')
            >>> tickets = results['results']
        """
        params = {
            "query": query,
            "page": page,
            "per_page": min(per_page, 100)  # Zendesk max is 100
        }

        response = await self._request("GET", "/search.json", params=params)
        logger.info(
            f"Search returned {len(response.get('results', []))} tickets "
            f"(page {page})"
        )

        return response

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """
        Get single ticket by ID.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            Ticket object dictionary

        Example:
            >>> ticket = await client.get_ticket(12345)
            >>> print(ticket['subject'])
        """
        response = await self._request("GET", f"/tickets/{ticket_id}.json")
        logger.info(f"Fetched ticket {ticket_id}")

        return response.get("ticket", {})

    async def get_ticket_comments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """
        Get all comments for a ticket (includes internal notes).

        Handles pagination automatically if there are many comments.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            List of comment objects. Each comment has:
                - id: Comment ID
                - type: "Comment" or "VoiceComment"
                - author_id: User ID of author
                - body: Comment text
                - html_body: Comment HTML
                - plain_body: Plain text version
                - public: Boolean - True for public, False for internal
                - created_at: ISO timestamp

        Example:
            >>> comments = await client.get_ticket_comments(12345)
            >>> internal = [c for c in comments if not c['public']]
        """
        all_comments = []
        next_page = f"/tickets/{ticket_id}/comments.json"

        while next_page:
            response = await self._request("GET", next_page)
            comments = response.get("comments", [])
            all_comments.extend(comments)

            # Get next page URL (relative path)
            next_page = response.get("next_page")
            if next_page:
                # Extract path from full URL
                next_page = next_page.replace(self.base_url, "")

        logger.info(
            f"Fetched {len(all_comments)} comments for ticket {ticket_id}"
        )

        return all_comments

    async def get_ticket_with_comments(
        self,
        ticket_id: int
    ) -> Dict[str, Any]:
        """
        Fetch ticket and all its comments, separating internal from public.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            Dictionary containing:
                - ticket: Ticket object
                - internal_notes: List of internal comments (public=False)
                - public_comments: List of public comments (public=True)
                - all_comments: All comments in chronological order

        Example:
            >>> data = await client.get_ticket_with_comments(12345)
            >>> ticket = data['ticket']
            >>> notes = data['internal_notes']
        """
        # Fetch ticket and comments in parallel
        ticket_task = self.get_ticket(ticket_id)
        comments_task = self.get_ticket_comments(ticket_id)

        ticket, comments = await asyncio.gather(ticket_task, comments_task)

        # Separate internal notes from public comments
        internal_notes = [c for c in comments if not c.get("public", True)]
        public_comments = [c for c in comments if c.get("public", True)]

        logger.info(
            f"Ticket {ticket_id}: {len(public_comments)} public, "
            f"{len(internal_notes)} internal"
        )

        return {
            "ticket": ticket,
            "internal_notes": internal_notes,
            "public_comments": public_comments,
            "all_comments": comments
        }

    async def paginate_search(
        self,
        query: str,
        page_size: int = 100
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Generator that yields batches of tickets from search.

        Handles pagination automatically using next_page URL.
        Continues until all results are fetched.

        Args:
            query: Zendesk search query
            page_size: Results per page (max 100)

        Yields:
            Lists of ticket objects (batches)

        Example:
            >>> async for batch in client.paginate_search('type:ticket'):
            ...     for ticket in batch:
            ...         print(ticket['id'])
        """
        page = 1
        total_fetched = 0

        while True:
            response = await self.search_tickets(
                query=query,
                page=page,
                per_page=page_size
            )

            results = response.get("results", [])
            if not results:
                break

            total_fetched += len(results)
            logger.info(
                f"Paginated search: fetched {len(results)} tickets "
                f"(total: {total_fetched})"
            )

            yield results

            # Check if there are more pages
            next_page = response.get("next_page")
            if not next_page:
                break

            page += 1

        logger.info(f"Search complete: {total_fetched} total tickets")

    def format_comments(self, comments: List[Dict[str, Any]]) -> str:
        """
        Format list of comments into readable text string.

        Includes author, timestamp, and body for each comment.
        Uses plain_body if available, otherwise body.

        Args:
            comments: List of comment objects from Zendesk API

        Returns:
            Formatted string with all comments

        Example:
            >>> formatted = client.format_comments(internal_notes)
            >>> print(formatted)
        """
        if not comments:
            return "(No comments)"

        formatted_parts = []

        for i, comment in enumerate(comments, 1):
            author_id = comment.get("author_id", "Unknown")
            created_at = comment.get("created_at", "")

            # Parse timestamp for better formatting
            timestamp = created_at
            try:
                dt = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, AttributeError):
                pass

            # Get comment body (prefer plain_body)
            body = (
                comment.get("plain_body") or
                comment.get("body") or
                "(empty comment)"
            )

            # Determine if internal or public
            comment_type = "Internal Note" if not comment.get("public", True) else "Public Comment"

            formatted_parts.append(
                f"--- Comment {i} ({comment_type}) ---\n"
                f"Author ID: {author_id}\n"
                f"Created: {timestamp}\n"
                f"\n{body}\n"
            )

        return "\n".join(formatted_parts)

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user information by ID.

        Args:
            user_id: Zendesk user ID

        Returns:
            User object dictionary
        """
        response = await self._request("GET", f"/users/{user_id}.json")
        return response.get("user", {})

    async def get_organization(self, org_id: int) -> Dict[str, Any]:
        """
        Get organization information by ID.

        Args:
            org_id: Zendesk organization ID

        Returns:
            Organization object dictionary
        """
        response = await self._request("GET", f"/organizations/{org_id}.json")
        return response.get("organization", {})


def get_zendesk_client() -> ZendeskClient:
    """
    Factory function to create Zendesk client with settings.

    Returns:
        Configured ZendeskClient instance

    Example:
        >>> client = get_zendesk_client()
        >>> async with client:
        ...     ticket = await client.get_ticket(12345)
    """
    from app.config import settings

    return ZendeskClient(
        subdomain=settings.ZENDESK_SUBDOMAIN,
        email=settings.ZENDESK_EMAIL,
        api_token=settings.ZENDESK_API_TOKEN
    )
