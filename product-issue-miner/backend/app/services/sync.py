"""
Sync service for fetching and storing Zendesk tickets.

This module provides the SyncService class that:
1. Fetches tickets from Zendesk based on date ranges
2. Upserts tickets to the database with deduplication
3. Tracks sync state and progress
4. Handles incremental and backfill syncs
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models import Ticket, SyncState
from app.services.zendesk import ZendeskClient, get_zendesk_client

logger = logging.getLogger(__name__)


class SyncService:
    """Handles syncing tickets from Zendesk to the database."""

    def __init__(self, db: AsyncSession, zendesk_client: ZendeskClient):
        """
        Initialize sync service.

        Args:
            db: Async database session
            zendesk_client: Configured Zendesk API client
        """
        self.db = db
        self.zendesk = zendesk_client
        self._is_running = False
        self._current_progress = None

    @property
    def is_running(self) -> bool:
        """Check if sync is currently running."""
        return self._is_running

    @property
    def current_progress(self) -> Optional[str]:
        """Get current sync progress message."""
        return self._current_progress

    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get the last successful sync timestamp from sync_state table.

        Returns:
            Last ticket update timestamp, or None if no sync has run
        """
        result = await self.db.execute(
            select(SyncState).order_by(SyncState.sync_completed_at.desc()).limit(1)
        )
        state = result.scalar_one_or_none()
        return state.last_ticket_updated_at if state else None

    async def sync_tickets(self, backfill_days: Optional[int] = None) -> dict:
        """
        Sync tickets from Zendesk.

        Args:
            backfill_days: If set, fetch tickets from last N days.
                          Otherwise, incremental sync from last sync time.

        Returns:
            Dict with sync stats: tickets_synced, errors

        Raises:
            RuntimeError: If sync is already in progress
        """
        if self._is_running:
            raise RuntimeError("Sync already in progress")

        self._is_running = True
        self._current_progress = "Starting sync..."
        tickets_synced = 0
        errors = 0

        try:
            # Determine start date
            if backfill_days:
                start_date = datetime.utcnow() - timedelta(days=backfill_days)
                logger.info(f"Starting backfill sync from {start_date}")
            else:
                start_date = await self.get_last_sync_timestamp()
                if not start_date:
                    # First sync - default to 1 day back
                    start_date = datetime.utcnow() - timedelta(days=1)
                logger.info(f"Starting incremental sync from {start_date}")

            # Build search query for Zendesk
            query = f"type:ticket updated>{start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"

            # Iterate through paginated results
            async for ticket_batch in self.zendesk.paginate_search(query):
                for ticket_data in ticket_batch:
                    try:
                        self._current_progress = f"Processing ticket {ticket_data['id']}"

                        # Fetch full ticket with comments
                        full_ticket = await self.zendesk.get_ticket_with_comments(ticket_data['id'])

                        # Upsert to database
                        await self._upsert_ticket(full_ticket)
                        tickets_synced += 1

                    except Exception as e:
                        logger.error(f"Error processing ticket {ticket_data['id']}: {e}")
                        errors += 1
                        continue

                # Commit batch
                await self.db.commit()
                self._current_progress = f"Synced {tickets_synced} tickets..."

            # Update sync state
            await self._update_sync_state(tickets_synced)

            logger.info(f"Sync complete: {tickets_synced} tickets synced, {errors} errors")
            return {"tickets_synced": tickets_synced, "errors": errors}

        finally:
            self._is_running = False
            self._current_progress = None

    async def _upsert_ticket(self, ticket_data: dict):
        """
        Insert or update a ticket in the database.

        Args:
            ticket_data: Dict from get_ticket_with_comments containing:
                        - ticket: Ticket object
                        - internal_notes: List of internal comments
                        - public_comments: List of public comments
        """
        ticket_info = ticket_data['ticket']

        # Format comments using Zendesk client's formatter
        internal_notes_text = self.zendesk.format_comments(ticket_data.get('internal_notes', []))
        public_comments_text = self.zendesk.format_comments(ticket_data.get('public_comments', []))

        # Get organization info if available
        requester_email = None
        requester_org_name = None
        zendesk_org_id = ticket_info.get('organization_id')

        # Fetch requester details if available
        requester_id = ticket_info.get('requester_id')
        if requester_id:
            try:
                requester = await self.zendesk.get_user(requester_id)
                requester_email = requester.get('email')
            except Exception as e:
                logger.warning(f"Could not fetch requester {requester_id}: {e}")

        # Fetch organization details if available
        if zendesk_org_id:
            try:
                org = await self.zendesk.get_organization(zendesk_org_id)
                requester_org_name = org.get('name')
            except Exception as e:
                logger.warning(f"Could not fetch organization {zendesk_org_id}: {e}")

        stmt = insert(Ticket).values(
            zendesk_ticket_id=ticket_info['id'],
            subject=ticket_info.get('subject'),
            description=ticket_info.get('description'),
            internal_notes=internal_notes_text,
            public_comments=public_comments_text,
            requester_email=requester_email,
            requester_org_name=requester_org_name,
            zendesk_org_id=zendesk_org_id,
            tags=ticket_info.get('tags', []),
            status=ticket_info.get('status'),
            priority=ticket_info.get('priority'),
            ticket_created_at=ticket_info['created_at'],
            ticket_updated_at=ticket_info['updated_at'],
            synced_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['zendesk_ticket_id'],
            set_={
                'subject': ticket_info.get('subject'),
                'description': ticket_info.get('description'),
                'internal_notes': internal_notes_text,
                'public_comments': public_comments_text,
                'requester_email': requester_email,
                'requester_org_name': requester_org_name,
                'tags': ticket_info.get('tags', []),
                'status': ticket_info.get('status'),
                'priority': ticket_info.get('priority'),
                'ticket_updated_at': ticket_info['updated_at'],
                'synced_at': datetime.utcnow()
            }
        )

        await self.db.execute(stmt)

    async def _update_sync_state(self, tickets_synced: int):
        """
        Record sync completion in sync_state table.

        Args:
            tickets_synced: Number of tickets synced in this run
        """
        sync_state = SyncState(
            last_ticket_updated_at=datetime.utcnow(),
            tickets_synced=tickets_synced,
            issues_extracted=0,  # Updated after analysis
            sync_completed_at=datetime.utcnow()
        )
        self.db.add(sync_state)
        await self.db.commit()

    async def get_sync_status(self) -> dict:
        """
        Get current sync status.

        Returns:
            Dict containing:
            - last_sync_at: Last sync completion timestamp
            - last_ticket_updated_at: Last ticket update timestamp
            - tickets_synced: Tickets synced in last run
            - issues_extracted: Issues extracted in last run
            - is_running: Whether sync is currently running
            - current_progress: Current progress message
        """
        last_state = await self.db.execute(
            select(SyncState).order_by(SyncState.sync_completed_at.desc()).limit(1)
        )
        state = last_state.scalar_one_or_none()

        return {
            "last_sync_at": state.sync_completed_at if state else None,
            "last_ticket_updated_at": state.last_ticket_updated_at if state else None,
            "tickets_synced": state.tickets_synced if state else 0,
            "issues_extracted": state.issues_extracted if state else 0,
            "is_running": self._is_running,
            "current_progress": self._current_progress
        }


def get_sync_service(db: AsyncSession) -> SyncService:
    """
    Factory function to create SyncService with dependencies.

    Args:
        db: Async database session

    Returns:
        Configured SyncService instance

    Example:
        >>> async with get_async_session() as db:
        ...     sync_service = get_sync_service(db)
        ...     await sync_service.sync_tickets(backfill_days=7)
    """
    zendesk_client = get_zendesk_client()
    return SyncService(db=db, zendesk_client=zendesk_client)
