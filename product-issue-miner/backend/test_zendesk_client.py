"""
Test script for Zendesk API client.

This script demonstrates basic usage of the ZendeskClient.
Run with: python test_zendesk_client.py
"""

import asyncio
import logging
from app.services import get_zendesk_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_search():
    """Test ticket search functionality."""
    client = get_zendesk_client()

    async with client:
        # Search for tickets with 'product_issue' tag
        logger.info("Searching for tickets with 'product_issue' tag...")
        results = await client.search_tickets(
            query="type:ticket tags:product_issue",
            per_page=10
        )

        tickets = results.get("results", [])
        logger.info(f"Found {len(tickets)} tickets")

        for ticket in tickets[:5]:  # Show first 5
            logger.info(
                f"  Ticket #{ticket['id']}: {ticket['subject']}"
            )


async def test_get_ticket_with_comments():
    """Test fetching a ticket with comments."""
    client = get_zendesk_client()

    async with client:
        # Replace with actual ticket ID
        ticket_id = 12345

        logger.info(f"Fetching ticket {ticket_id} with comments...")
        data = await client.get_ticket_with_comments(ticket_id)

        ticket = data["ticket"]
        logger.info(f"Ticket: {ticket['subject']}")
        logger.info(f"Status: {ticket['status']}")
        logger.info(f"Public comments: {len(data['public_comments'])}")
        logger.info(f"Internal notes: {len(data['internal_notes'])}")

        # Format and display internal notes
        if data['internal_notes']:
            logger.info("\nInternal Notes:")
            formatted = client.format_comments(data['internal_notes'])
            print(formatted[:500])  # Show first 500 chars


async def test_paginated_search():
    """Test paginated search."""
    client = get_zendesk_client()

    async with client:
        logger.info("Testing paginated search...")
        total_tickets = 0

        async for batch in client.paginate_search(
            query="type:ticket status:open",
            page_size=50
        ):
            total_tickets += len(batch)
            logger.info(f"  Processed batch of {len(batch)} tickets")

            # Stop after 3 batches for testing
            if total_tickets >= 150:
                break

        logger.info(f"Total tickets processed: {total_tickets}")


async def main():
    """Run all tests."""
    logger.info("=== Zendesk Client Test Suite ===\n")

    try:
        # Test 1: Search
        await test_search()
        logger.info("\n" + "="*50 + "\n")

        # Test 2: Get ticket with comments
        # Uncomment and set valid ticket ID to test
        # await test_get_ticket_with_comments()
        # logger.info("\n" + "="*50 + "\n")

        # Test 3: Paginated search
        # Uncomment to test pagination
        # await test_paginated_search()

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
