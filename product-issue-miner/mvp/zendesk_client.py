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

    def fetch_tickets(self, days_back: int = 7, limit: int = 100) -> list[dict]:
        """Fetch recent tickets, optionally filtered by brand."""
        since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Build search query
        query_parts = [f"type:ticket", f"created>{since_date}"]
        if Config.ZENDESK_BRAND_ID:
            query_parts.append(f"brand_id:{Config.ZENDESK_BRAND_ID}")

        query = " ".join(query_parts)

        tickets = []
        url = f"{self.base_url}/search.json"
        params = {"query": query, "sort_by": "created_at", "sort_order": "desc"}

        with httpx.Client(auth=self.auth, timeout=30.0) as client:
            while url and len(tickets) < limit:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for ticket in data.get("results", []):
                    if len(tickets) >= limit:
                        break
                    tickets.append(ticket)

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
    tickets = client.fetch_tickets(days_back=7, limit=5)
    rprint(f"[green]Found {len(tickets)} tickets[/green]")

    for t in tickets:
        rprint(f"  - #{t['id']}: {t['subject'][:60]}...")
