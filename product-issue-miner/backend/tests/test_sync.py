"""
Tests for sync service.

Tests cover:
- Incremental sync
- Backfill sync
- Ticket upsert logic
- Sync state tracking
- Error handling during sync
- Comment aggregation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ticket, SyncState
from app.services.sync import SyncService


@pytest.mark.asyncio
@pytest.mark.sync
class TestSyncService:
    """Test suite for SyncService."""

    async def test_sync_initialization(
        self, db_session: AsyncSession, mock_zendesk_client
    ):
        """Test sync service initialization."""
        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        assert service.db == db_session
        assert service.zendesk == mock_zendesk_client
        assert service.is_running is False
        assert service.current_progress is None

    async def test_get_last_sync_timestamp_none(self, db_session: AsyncSession, mock_zendesk_client):
        """Test getting last sync timestamp when no sync has run."""
        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        timestamp = await service.get_last_sync_timestamp()
        assert timestamp is None

    async def test_get_last_sync_timestamp(
        self, db_session: AsyncSession, mock_zendesk_client
    ):
        """Test getting last sync timestamp from sync_state."""
        # Create sync state
        last_sync = datetime.utcnow() - timedelta(hours=1)
        sync_state = SyncState(
            last_ticket_updated_at=last_sync,
            tickets_synced=10,
            issues_extracted=5,
            sync_completed_at=datetime.utcnow(),
        )
        db_session.add(sync_state)
        await db_session.commit()

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        timestamp = await service.get_last_sync_timestamp()

        assert timestamp == last_sync

    async def test_sync_tickets_incremental(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test incremental sync from last sync time."""
        # Mock paginated search to return one batch
        async def mock_paginate_search(query):
            yield [sample_ticket_with_comments["ticket"]]

        mock_zendesk_client.paginate_search = mock_paginate_search
        mock_zendesk_client.get_ticket_with_comments.return_value = (
            sample_ticket_with_comments
        )

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        result = await service.sync_tickets(backfill_days=None)

        assert result["tickets_synced"] == 1
        assert result["errors"] == 0

        # Verify ticket was created
        query_result = await db_session.execute(select(Ticket))
        tickets = query_result.scalars().all()
        assert len(tickets) == 1
        assert tickets[0].zendesk_ticket_id == sample_ticket_with_comments["ticket"]["id"]

    async def test_sync_tickets_backfill(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test backfill sync for last N days."""
        async def mock_paginate_search(query):
            yield [sample_ticket_with_comments["ticket"]]

        mock_zendesk_client.paginate_search = mock_paginate_search
        mock_zendesk_client.get_ticket_with_comments.return_value = (
            sample_ticket_with_comments
        )

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        result = await service.sync_tickets(backfill_days=7)

        assert result["tickets_synced"] == 1

    async def test_sync_tickets_updates_existing(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test that sync updates existing tickets (upsert)."""
        # Create initial ticket
        existing_ticket = Ticket(
            zendesk_ticket_id=sample_ticket_with_comments["ticket"]["id"],
            subject="Old subject",
            status="open",
            ticket_created_at=datetime.utcnow() - timedelta(days=1),
            ticket_updated_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(existing_ticket)
        await db_session.commit()

        # Mock sync with updated ticket data
        updated_ticket_data = sample_ticket_with_comments.copy()
        updated_ticket_data["ticket"]["subject"] = "Updated subject"

        async def mock_paginate_search(query):
            yield [updated_ticket_data["ticket"]]

        mock_zendesk_client.paginate_search = mock_paginate_search
        mock_zendesk_client.get_ticket_with_comments.return_value = updated_ticket_data

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        await service.sync_tickets(backfill_days=1)

        # Verify ticket was updated, not duplicated
        query_result = await db_session.execute(select(Ticket))
        tickets = query_result.scalars().all()
        assert len(tickets) == 1
        assert tickets[0].subject == "Updated subject"

    async def test_sync_multiple_tickets(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test syncing multiple tickets in batch."""
        tickets_data = [
            {
                "id": 111,
                "subject": "Ticket 1",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
            },
            {
                "id": 222,
                "subject": "Ticket 2",
                "created_at": "2024-01-15T11:00:00Z",
                "updated_at": "2024-01-15T11:00:00Z",
            },
        ]

        async def mock_paginate_search(query):
            yield tickets_data

        mock_zendesk_client.paginate_search = mock_paginate_search

        # Mock get_ticket_with_comments to return data for each ticket
        def mock_get_ticket(ticket_id):
            ticket = next(t for t in tickets_data if t["id"] == ticket_id)
            return {
                "ticket": ticket,
                "public_comments": [],
                "internal_notes": [],
                "all_comments": [],
            }

        mock_zendesk_client.get_ticket_with_comments.side_effect = mock_get_ticket

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        result = await service.sync_tickets(backfill_days=1)

        assert result["tickets_synced"] == 2

        query_result = await db_session.execute(select(Ticket))
        tickets = query_result.scalars().all()
        assert len(tickets) == 2

    async def test_sync_handles_errors(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test that sync handles individual ticket errors gracefully."""
        tickets_data = [
            {
                "id": 111,
                "subject": "Good ticket",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
            },
            {
                "id": 222,
                "subject": "Bad ticket",
                "created_at": "2024-01-15T11:00:00Z",
                "updated_at": "2024-01-15T11:00:00Z",
            },
        ]

        async def mock_paginate_search(query):
            yield tickets_data

        mock_zendesk_client.paginate_search = mock_paginate_search

        # Mock to raise error on second ticket
        def mock_get_ticket(ticket_id):
            if ticket_id == 222:
                raise Exception("Failed to fetch ticket")
            return {
                "ticket": tickets_data[0],
                "public_comments": [],
                "internal_notes": [],
                "all_comments": [],
            }

        mock_zendesk_client.get_ticket_with_comments.side_effect = mock_get_ticket

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        result = await service.sync_tickets(backfill_days=1)

        # Should sync one and error on one
        assert result["tickets_synced"] == 1
        assert result["errors"] == 1

    async def test_sync_creates_sync_state(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test that sync creates sync_state record."""
        async def mock_paginate_search(query):
            return
            yield  # Empty generator

        mock_zendesk_client.paginate_search = mock_paginate_search

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        await service.sync_tickets(backfill_days=1)

        # Verify sync state was created
        query_result = await db_session.execute(select(SyncState))
        sync_states = query_result.scalars().all()
        assert len(sync_states) == 1
        assert sync_states[0].sync_completed_at is not None

    async def test_sync_already_running_error(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test that sync raises error if already running."""
        async def mock_paginate_search(query):
            return
            yield

        mock_zendesk_client.paginate_search = mock_paginate_search

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        # Set sync as running
        service._is_running = True

        with pytest.raises(RuntimeError, match="already in progress"):
            await service.sync_tickets(backfill_days=1)

    async def test_get_sync_status(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test getting sync status."""
        # Create sync state
        sync_state = SyncState(
            last_ticket_updated_at=datetime.utcnow() - timedelta(hours=1),
            tickets_synced=50,
            issues_extracted=25,
            sync_completed_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db_session.add(sync_state)
        await db_session.commit()

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        status = await service.get_sync_status()

        assert status["tickets_synced"] == 50
        assert status["issues_extracted"] == 25
        assert status["is_running"] is False
        assert status["last_sync_at"] is not None

    async def test_upsert_ticket_with_comments(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test ticket upsert includes formatted comments."""
        mock_zendesk_client.format_comments.side_effect = lambda comments: (
            "Formatted: " + str(len(comments)) + " comments"
        )

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        await service._upsert_ticket(sample_ticket_with_comments)

        # Verify ticket was created with comments
        query_result = await db_session.execute(select(Ticket))
        ticket = query_result.scalar_one()

        assert "Formatted:" in ticket.internal_notes
        assert "Formatted:" in ticket.public_comments

    async def test_upsert_ticket_fetches_requester_info(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test that upsert fetches requester and org info."""
        mock_zendesk_client.get_user.return_value = {
            "id": 67890,
            "email": "user@example.com",
        }
        mock_zendesk_client.get_organization.return_value = {
            "id": 11111,
            "name": "Example Corp",
        }

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        await service._upsert_ticket(sample_ticket_with_comments)

        query_result = await db_session.execute(select(Ticket))
        ticket = query_result.scalar_one()

        assert ticket.requester_email == "user@example.com"
        assert ticket.requester_org_name == "Example Corp"

    async def test_sync_default_backfill_first_run(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test that first sync defaults to 1 day backfill."""
        async def mock_paginate_search(query):
            # Verify query contains updated> date filter
            assert "updated>" in query
            return
            yield

        mock_zendesk_client.paginate_search = mock_paginate_search

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        # First sync with no backfill_days should default to 1 day
        await service.sync_tickets(backfill_days=None)

    async def test_sync_progress_tracking(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
        sample_ticket_with_comments,
    ):
        """Test that sync tracks progress during execution."""
        async def mock_paginate_search(query):
            yield [sample_ticket_with_comments["ticket"]]

        mock_zendesk_client.paginate_search = mock_paginate_search
        mock_zendesk_client.get_ticket_with_comments.return_value = (
            sample_ticket_with_comments
        )

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        # Check progress during sync (would need async monitoring in real scenario)
        result = await service.sync_tickets(backfill_days=1)

        # After sync, progress should be cleared
        assert service.current_progress is None
        assert service.is_running is False


@pytest.mark.asyncio
@pytest.mark.sync
class TestSyncServiceEdgeCases:
    """Test edge cases and error scenarios."""

    async def test_sync_empty_results(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test sync with no tickets to sync."""
        async def mock_paginate_search(query):
            return
            yield  # Empty generator

        mock_zendesk_client.paginate_search = mock_paginate_search

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)
        result = await service.sync_tickets(backfill_days=1)

        assert result["tickets_synced"] == 0
        assert result["errors"] == 0

    async def test_upsert_ticket_missing_requester(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test upsert when requester info cannot be fetched."""
        ticket_data = {
            "ticket": {
                "id": 999,
                "subject": "Test",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "requester_id": 123,
            },
            "public_comments": [],
            "internal_notes": [],
        }

        # Mock get_user to raise error
        mock_zendesk_client.get_user.side_effect = Exception("User not found")
        mock_zendesk_client.format_comments.return_value = ""

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        # Should not raise, should handle gracefully
        await service._upsert_ticket(ticket_data)

        query_result = await db_session.execute(select(Ticket))
        ticket = query_result.scalar_one()

        # Requester email should be None
        assert ticket.requester_email is None

    async def test_sync_state_incremental_updates(
        self,
        db_session: AsyncSession,
        mock_zendesk_client,
    ):
        """Test that multiple syncs create multiple sync states."""
        async def mock_paginate_search(query):
            return
            yield

        mock_zendesk_client.paginate_search = mock_paginate_search

        service = SyncService(db=db_session, zendesk_client=mock_zendesk_client)

        # Run sync twice
        await service.sync_tickets(backfill_days=1)
        await service.sync_tickets(backfill_days=1)

        # Should have two sync state records
        query_result = await db_session.execute(select(SyncState))
        sync_states = query_result.scalars().all()
        assert len(sync_states) == 2
