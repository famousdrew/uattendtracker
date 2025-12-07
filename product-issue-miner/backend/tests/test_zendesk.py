"""
Tests for Zendesk API client.

Tests cover:
- Authentication
- Ticket search with pagination
- Ticket retrieval with comments
- Rate limiting logic
- Error handling and retries
- Comment formatting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import httpx

from app.services.zendesk import (
    ZendeskClient,
    ZendeskAPIError,
    ZendeskRateLimitError,
)


@pytest.mark.asyncio
@pytest.mark.zendesk
class TestZendeskClient:
    """Test suite for ZendeskClient."""

    def test_client_initialization(self):
        """Test client initialization with credentials."""
        client = ZendeskClient(
            subdomain="testcompany",
            email="test@example.com",
            api_token="test_token_12345",
        )

        assert client.base_url == "https://testcompany.zendesk.com/api/v2"
        assert client.auth_header is not None
        assert client.RATE_LIMIT == 700

    async def test_context_manager(self):
        """Test async context manager functionality."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        async with client as c:
            assert c._client is not None

        # Client should be closed after context
        assert client._client is None

    async def test_search_tickets_success(self, mock_zendesk_client):
        """Test successful ticket search."""
        mock_response = {
            "results": [
                {"id": 123, "subject": "Test ticket 1"},
                {"id": 456, "subject": "Test ticket 2"},
            ],
            "count": 2,
            "next_page": None,
            "previous_page": None,
        }

        mock_zendesk_client.search_tickets.return_value = mock_response

        result = await mock_zendesk_client.search_tickets("type:ticket")

        assert len(result["results"]) == 2
        assert result["count"] == 2
        mock_zendesk_client.search_tickets.assert_called_once()

    async def test_search_tickets_with_pagination(self):
        """Test ticket search with pagination parameters."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "results": [],
                "count": 0,
                "next_page": None,
            }

            await client.search_tickets(
                query="type:ticket",
                page=2,
                per_page=50,
            )

            # Verify request was called with correct params
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["params"]["page"] == 2
            assert call_args[1]["params"]["per_page"] == 50

    async def test_get_ticket_success(self, sample_zendesk_ticket):
        """Test successful single ticket retrieval."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"ticket": sample_zendesk_ticket}

            ticket = await client.get_ticket(12345)

            assert ticket["id"] == 12345
            assert ticket["subject"] == sample_zendesk_ticket["subject"]
            mock_request.assert_called_once_with("GET", "/tickets/12345.json")

    async def test_get_ticket_comments(self, sample_zendesk_comments):
        """Test fetching ticket comments."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "comments": sample_zendesk_comments,
                "next_page": None,
            }

            comments = await client.get_ticket_comments(12345)

            assert len(comments) == 2
            assert comments[0]["id"] == 1
            assert comments[1]["public"] is False

    async def test_get_ticket_comments_pagination(self):
        """Test comment pagination handling."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        # Mock paginated responses
        page1_response = {
            "comments": [{"id": 1, "body": "Comment 1"}],
            "next_page": "https://test.zendesk.com/api/v2/tickets/123/comments.json?page=2",
        }
        page2_response = {
            "comments": [{"id": 2, "body": "Comment 2"}],
            "next_page": None,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [page1_response, page2_response]

            comments = await client.get_ticket_comments(123)

            assert len(comments) == 2
            assert mock_request.call_count == 2

    async def test_get_ticket_with_comments(
        self, sample_zendesk_ticket, sample_zendesk_comments
    ):
        """Test fetching ticket with separated comments."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "get_ticket", new_callable=AsyncMock) as mock_get:
            with patch.object(
                client, "get_ticket_comments", new_callable=AsyncMock
            ) as mock_comments:
                mock_get.return_value = sample_zendesk_ticket
                mock_comments.return_value = sample_zendesk_comments

                result = await client.get_ticket_with_comments(12345)

                assert result["ticket"] == sample_zendesk_ticket
                assert len(result["public_comments"]) == 1
                assert len(result["internal_notes"]) == 1
                assert result["public_comments"][0]["public"] is True
                assert result["internal_notes"][0]["public"] is False

    async def test_format_comments(self):
        """Test comment formatting."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        comments = [
            {
                "id": 1,
                "author_id": 123,
                "body": "Test comment",
                "public": True,
                "created_at": "2024-01-15T10:30:00Z",
            }
        ]

        formatted = client.format_comments(comments)

        assert "Test comment" in formatted
        assert "Author ID: 123" in formatted
        assert "Public Comment" in formatted

    async def test_format_comments_empty(self):
        """Test formatting empty comment list."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        formatted = client.format_comments([])
        assert formatted == "(No comments)"

    async def test_rate_limit_enforcement(self):
        """Test rate limiting logic."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        # Set request count to near limit
        client._request_count = client.RATE_LIMIT - 1

        # Mock the sleep to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._check_rate_limit()

            # Should not sleep yet
            mock_sleep.assert_not_called()

            # Next request should trigger sleep
            await client._check_rate_limit()
            mock_sleep.assert_called_once()

    async def test_rate_limit_429_retry(self):
        """Test handling 429 rate limit response."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        # Create mock responses: first 429, then success
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "1"}

        response_success = MagicMock()
        response_success.status_code = 200
        response_success.json.return_value = {"success": True}

        with patch.object(
            client, "_ensure_client", new_callable=AsyncMock
        ) as mock_ensure:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                client._client = MagicMock()
                client._client.request = AsyncMock(
                    side_effect=[response_429, response_success]
                )

                result = await client._request("GET", "/test.json")

                assert result == {"success": True}
                mock_sleep.assert_called()

    async def test_server_error_retry(self):
        """Test retry logic for 5xx server errors."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        response_500 = MagicMock()
        response_500.status_code = 500
        response_500.text = "Internal Server Error"

        response_success = MagicMock()
        response_success.status_code = 200
        response_success.json.return_value = {"success": True}

        with patch.object(client, "_ensure_client", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                client._client = MagicMock()
                client._client.request = AsyncMock(
                    side_effect=[response_500, response_success]
                )

                result = await client._request("GET", "/test.json")

                assert result == {"success": True}
                mock_sleep.assert_called()

    async def test_max_retries_exceeded(self):
        """Test that max retries raises error."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        response_500 = MagicMock()
        response_500.status_code = 500
        response_500.text = "Server Error"

        with patch.object(client, "_ensure_client", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                client._client = MagicMock()
                client._client.request = AsyncMock(return_value=response_500)

                with pytest.raises(ZendeskAPIError):
                    await client._request("GET", "/test.json")

    async def test_client_error_no_retry(self):
        """Test that 4xx client errors don't retry (except 429)."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        response_404 = MagicMock()
        response_404.status_code = 404
        response_404.text = "Not Found"
        response_404.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=response_404
        )

        with patch.object(client, "_ensure_client", new_callable=AsyncMock):
            client._client = MagicMock()
            client._client.request = AsyncMock(return_value=response_404)

            with pytest.raises(ZendeskAPIError):
                await client._request("GET", "/test.json")

    async def test_paginate_search(self):
        """Test paginated search generator."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        # Mock responses for 3 pages
        responses = [
            {
                "results": [{"id": 1}, {"id": 2}],
                "next_page": "url",
            },
            {
                "results": [{"id": 3}, {"id": 4}],
                "next_page": "url",
            },
            {
                "results": [{"id": 5}],
                "next_page": None,
            },
        ]

        with patch.object(client, "search_tickets", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = responses

            all_tickets = []
            async for batch in client.paginate_search("type:ticket"):
                all_tickets.extend(batch)

            assert len(all_tickets) == 5
            assert mock_search.call_count == 3

    async def test_get_user(self):
        """Test fetching user information."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "user": {"id": 123, "name": "Test User", "email": "test@example.com"}
            }

            user = await client.get_user(123)

            assert user["id"] == 123
            assert user["email"] == "test@example.com"

    async def test_get_organization(self):
        """Test fetching organization information."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "organization": {"id": 456, "name": "Test Corp"}
            }

            org = await client.get_organization(456)

            assert org["id"] == 456
            assert org["name"] == "Test Corp"


@pytest.mark.asyncio
@pytest.mark.zendesk
class TestZendeskClientEdgeCases:
    """Test edge cases and error scenarios."""

    async def test_empty_search_results(self):
        """Test handling empty search results."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        with patch.object(client, "search_tickets", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "count": 0, "next_page": None}

            all_tickets = []
            async for batch in client.paginate_search("type:ticket"):
                all_tickets.extend(batch)

            assert len(all_tickets) == 0

    async def test_format_comments_with_missing_fields(self):
        """Test formatting comments with missing optional fields."""
        client = ZendeskClient(
            subdomain="test",
            email="test@example.com",
            api_token="token",
        )

        comments = [
            {
                "id": 1,
                # Missing author_id, created_at, body
            }
        ]

        formatted = client.format_comments(comments)

        assert "Author ID: Unknown" in formatted
        assert "(empty comment)" in formatted
