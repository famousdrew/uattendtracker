"""
Analysis pipeline for processing tickets and extracting issues.

This module provides the AnalysisPipeline class that:
1. Processes unanalyzed tickets using Claude AI
2. Extracts product issues and saves to database
3. Orchestrates the full pipeline (sync -> analyze -> cluster -> trends)
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Ticket, ExtractedIssue
from app.services.analyzer import IssueAnalyzer, get_analyzer

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates the ticket analysis pipeline."""

    def __init__(self, db: AsyncSession, analyzer: IssueAnalyzer):
        """
        Initialize analysis pipeline.

        Args:
            db: Async database session
            analyzer: Configured IssueAnalyzer instance
        """
        self.db = db
        self.analyzer = analyzer
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if analysis is currently running."""
        return self._is_running

    async def analyze_unprocessed_tickets(self, batch_size: int = 500) -> dict:
        """
        Process tickets that haven't been analyzed yet.

        Args:
            batch_size: Number of tickets to process in one run

        Returns:
            Dict with stats: tickets_processed, issues_extracted, errors

        Raises:
            RuntimeError: If analysis is already in progress
        """
        if self._is_running:
            raise RuntimeError("Analysis already in progress")

        self._is_running = True
        tickets_processed = 0
        issues_extracted = 0
        errors = 0

        try:
            # Get unprocessed tickets (where analyzed_at is NULL)
            result = await self.db.execute(
                select(Ticket)
                .where(Ticket.analyzed_at.is_(None))
                .order_by(Ticket.ticket_created_at.desc())
                .limit(batch_size)
            )
            tickets = result.scalars().all()

            logger.info(f"Found {len(tickets)} unprocessed tickets")

            for ticket in tickets:
                try:
                    extracted = await self._process_single_ticket(ticket)
                    tickets_processed += 1
                    issues_extracted += extracted

                    # Commit every 10 tickets
                    if tickets_processed % 10 == 0:
                        await self.db.commit()
                        logger.info(
                            f"Processed {tickets_processed} tickets, "
                            f"{issues_extracted} issues extracted"
                        )

                except Exception as e:
                    logger.error(
                        f"Error analyzing ticket {ticket.zendesk_ticket_id}: {e}"
                    )
                    errors += 1
                    continue

            # Final commit
            await self.db.commit()

            logger.info(
                f"Analysis complete: {tickets_processed} tickets, "
                f"{issues_extracted} issues, {errors} errors"
            )
            return {
                "tickets_processed": tickets_processed,
                "issues_extracted": issues_extracted,
                "errors": errors
            }

        finally:
            self._is_running = False

    async def _process_single_ticket(self, ticket: Ticket) -> int:
        """
        Analyze a single ticket and save extracted issues.

        Args:
            ticket: Ticket model instance to analyze

        Returns:
            Number of issues extracted
        """
        # Build ticket dict for analyzer
        ticket_dict = {
            'zendesk_ticket_id': ticket.zendesk_ticket_id,
            'subject': ticket.subject,
            'description': ticket.description,
            'public_comments': ticket.public_comments,
            'internal_notes': ticket.internal_notes,
            'requester_email': ticket.requester_email,
            'requester_org_name': ticket.requester_org_name,
            'tags': ticket.tags or [],
            'ticket_created_at': ticket.ticket_created_at.isoformat() if ticket.ticket_created_at else None
        }

        # Call Claude for analysis
        result = self.analyzer.extract_issues(ticket_dict)

        # Save extracted issues
        for issue_data in result.get('issues', []):
            issue = ExtractedIssue(
                ticket_id=ticket.id,
                category=issue_data['category'],
                subcategory=issue_data['subcategory'],
                issue_type=issue_data['issue_type'],
                severity=issue_data['severity'],
                summary=issue_data['summary'],
                detail=issue_data.get('detail'),
                representative_quote=issue_data.get('representative_quote'),
                confidence=issue_data.get('confidence'),
                extracted_at=datetime.utcnow()
            )
            self.db.add(issue)

        # Mark ticket as analyzed
        ticket.analyzed_at = datetime.utcnow()

        return len(result.get('issues', []))

    async def run_full_pipeline(
        self,
        sync_service,
        clusterer=None,
        backfill_days: Optional[int] = None
    ) -> dict:
        """
        Run the complete pipeline: sync -> analyze -> cluster -> trends.

        Args:
            sync_service: SyncService instance for fetching tickets
            clusterer: Optional clustering service (not yet implemented)
            backfill_days: Number of days to backfill, or None for incremental

        Returns:
            Combined stats from all stages

        Note:
            The clustering and trend analysis stages are optional and will
            only run if a clusterer service is provided. This allows the
            pipeline to run without clustering initially.
        """
        results = {}

        # Step 1: Sync tickets from Zendesk
        logger.info("Starting sync...")
        results['sync'] = await sync_service.sync_tickets(backfill_days)

        # Step 2: Analyze unprocessed tickets
        logger.info("Starting analysis...")
        results['analysis'] = await self.analyze_unprocessed_tickets()

        # Step 3: Cluster issues (if clusterer provided)
        if clusterer:
            logger.info("Starting clustering...")
            try:
                results['clustering'] = await clusterer.cluster_issues()

                # Step 4: Update trends
                logger.info("Updating trends...")
                await clusterer.update_cluster_trends()
            except Exception as e:
                logger.error(f"Clustering failed: {e}")
                results['clustering'] = {"error": str(e)}
        else:
            logger.info("Skipping clustering (no clusterer provided)")
            results['clustering'] = {"skipped": True}

        logger.info("Pipeline complete")
        return results


def get_pipeline(db: AsyncSession) -> AnalysisPipeline:
    """
    Factory function to create AnalysisPipeline with dependencies.

    Args:
        db: Async database session

    Returns:
        Configured AnalysisPipeline instance

    Example:
        >>> async with get_async_session() as db:
        ...     pipeline = get_pipeline(db)
        ...     await pipeline.analyze_unprocessed_tickets()
    """
    analyzer = get_analyzer()
    return AnalysisPipeline(db=db, analyzer=analyzer)
