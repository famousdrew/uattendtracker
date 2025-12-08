"""Simple Zendesk client for fetching tickets."""
import httpx
from datetime import datetime, timedelta
from config import Config


class ZendeskClient:
    """Minimal Zendesk API client."""

    def __init__(self):
        self.base_url = f"https://{Config.ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"
        self.auth = (f"{Config.ZENDESK_EMAIL}/token", Config.ZENDESK_API_TOKEN)

    def test_connection(self) -> dict:
        """Test that we can connect to Zendesk."""
        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            response = client.get(f"{self.base_url}/users/me.json")
            response.raise_for_status()
            return response.json()

    def fetch_tickets(self, days_back: int = 7) -> list[dict]:
        """Fetch tickets in date range, optionally filtered by brand.

        Note: Zendesk search API limits to 1000 results (10 pages).
        For large date ranges, we fetch in smaller chunks to get all tickets.
        With ~1200 tickets/week, we use 5-day chunks to stay under 1000 limit.
        """
        all_tickets = []
        chunk_days = 5  # ~850 tickets per chunk at 1200/week rate

        # For ranges > chunk size, split into smaller intervals
        if days_back > chunk_days:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            current_end = end_date
            while current_end > start_date:
                current_start = max(current_end - timedelta(days=chunk_days), start_date)
                chunk_tickets = self._fetch_tickets_range(
                    current_start.strftime("%Y-%m-%d"),
                    current_end.strftime("%Y-%m-%d")
                )
                all_tickets.extend(chunk_tickets)
                current_end = current_start - timedelta(days=1)

            # Deduplicate by ticket ID
            seen_ids = set()
            unique_tickets = []
            for t in all_tickets:
                if t["id"] not in seen_ids:
                    seen_ids.add(t["id"])
                    unique_tickets.append(t)
            return unique_tickets
        else:
            # Small range - fetch directly but still respect the limit
            since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            return self._fetch_tickets_range(since_date)

    def _fetch_tickets_range(self, start_date: str, end_date: str = None) -> list[dict]:
        """Fetch tickets in a specific date range."""
        # Build search query
        query_parts = ["type:ticket", f"created>{start_date}"]
        if end_date:
            query_parts.append(f"created<{end_date}")
        if Config.ZENDESK_BRAND_ID:
            query_parts.append(f"brand_id:{Config.ZENDESK_BRAND_ID}")

        query = " ".join(query_parts)

        tickets = []
        url = f"{self.base_url}/search.json"
        params = {"query": query, "sort_by": "created_at", "sort_order": "desc"}
        page_count = 0
        max_pages = 10  # Zendesk limit

        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            while url and page_count < max_pages:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                tickets.extend(data.get("results", []))
                page_count += 1

                # Clear params for pagination (next_page includes them)
                params = None
                url = data.get("next_page")

        return tickets

    def get_ticket_comments(self, ticket_id: int) -> list[dict]:
        """Fetch all comments for a ticket."""
        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            response = client.get(f"{self.base_url}/tickets/{ticket_id}/comments.json")
            response.raise_for_status()
            return response.json().get("comments", [])


if __name__ == "__main__":
    # Quick test
    from rich import print as rprint

    missing = Config.validate()
    if missing:
        rprint(f"[red]Missing config: {missing}[/red]")
        exit(1)

    client = ZendeskClient()

    rprint("[blue]Testing Zendesk connection...[/blue]")
    try:
        user = client.test_connection()
        rprint(f"[green]Connected as: {user['user']['name']} ({user['user']['email']})[/green]")
    except Exception as e:
        rprint(f"[red]Connection failed: {e}[/red]")
        exit(1)

    rprint("\n[blue]Fetching recent tickets...[/blue]")
    tickets = client.fetch_tickets(days_back=7)
    rprint(f"[green]Found {len(tickets)} tickets[/green]")

    for t in tickets:
        rprint(f"  - #{t['id']}: {t['subject'][:60]}...")
