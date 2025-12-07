"""
Clustering service for grouping similar product issues.

This module provides the ClusteringService class that:
1. Groups unclustered issues into clusters based on similarity
2. Names clusters using Claude AI
3. Calculates trend metrics (7-day rolling trends)
4. Tracks unique customer counts per cluster
5. Supports cluster merging operations
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.models import ExtractedIssue, IssueCluster, Ticket
from app.services.analyzer import IssueAnalyzer, get_analyzer

logger = logging.getLogger(__name__)


class ClusteringService:
    """Groups similar issues into clusters and calculates trends."""

    SIMILARITY_THRESHOLD = 0.3  # Keyword overlap threshold

    def __init__(self, db: AsyncSession, analyzer: Optional[IssueAnalyzer] = None):
        """
        Initialize the clustering service.

        Args:
            db: Async database session
            analyzer: Optional IssueAnalyzer instance (will create one if not provided)
        """
        self.db = db
        self.analyzer = analyzer or get_analyzer()

    async def cluster_issues(self) -> dict:
        """
        Group unclustered issues into clusters.

        Algorithm:
        1. Get all issues where cluster_id is NULL
        2. Group by (category, subcategory)
        3. For each group:
           - Find existing active clusters
           - Try to match issues to clusters using keyword overlap
           - Create new clusters for unmatched issues
        4. Name new clusters using Claude

        Returns:
            Dict with stats: issues_clustered, new_clusters_created
        """
        issues_clustered = 0
        new_clusters_created = 0

        # Get unclustered issues
        result = await self.db.execute(
            select(ExtractedIssue).where(ExtractedIssue.cluster_id.is_(None))
        )
        unclustered = result.scalars().all()

        if not unclustered:
            logger.info("No unclustered issues found")
            return {"issues_clustered": 0, "new_clusters_created": 0}

        logger.info(f"Found {len(unclustered)} unclustered issues")

        # Group by category + subcategory
        grouped = defaultdict(list)
        for issue in unclustered:
            key = (issue.category, issue.subcategory)
            grouped[key].append(issue)

        # Process each group
        for (category, subcategory), issues in grouped.items():
            # Get existing active clusters for this category/subcategory
            existing_result = await self.db.execute(
                select(IssueCluster).where(
                    IssueCluster.category == category,
                    IssueCluster.subcategory == subcategory,
                    IssueCluster.is_active == True
                )
            )
            existing_clusters = list(existing_result.scalars().all())

            for issue in issues:
                # Try to find matching cluster
                matched = self._find_matching_cluster(issue, existing_clusters)

                if matched:
                    issue.cluster_id = matched.id
                    matched.issue_count += 1
                    matched.last_seen = issue.extracted_at or datetime.utcnow()
                    issues_clustered += 1
                else:
                    # Create new cluster with temporary name
                    new_cluster = IssueCluster(
                        category=category,
                        subcategory=subcategory,
                        cluster_name=f"New: {issue.summary[:50]}",
                        issue_count=1,
                        first_seen=issue.extracted_at or datetime.utcnow(),
                        last_seen=issue.extracted_at or datetime.utcnow()
                    )
                    self.db.add(new_cluster)
                    await self.db.flush()  # Get the ID

                    issue.cluster_id = new_cluster.id
                    existing_clusters.append(new_cluster)
                    issues_clustered += 1
                    new_clusters_created += 1

        await self.db.commit()

        # Name new clusters
        await self._name_unnamed_clusters()

        logger.info(
            f"Clustering complete: {issues_clustered} issues clustered, "
            f"{new_clusters_created} new clusters"
        )
        return {
            "issues_clustered": issues_clustered,
            "new_clusters_created": new_clusters_created
        }

    def _find_matching_cluster(
        self,
        issue: ExtractedIssue,
        clusters: List[IssueCluster]
    ) -> Optional[IssueCluster]:
        """
        Find best matching cluster using keyword overlap.

        Simple keyword-based approach - can upgrade to embeddings later.

        Args:
            issue: Issue to match
            clusters: List of candidate clusters

        Returns:
            Best matching cluster or None if no match found
        """
        if not clusters:
            return None

        issue_words = set(issue.summary.lower().split())

        best_match = None
        best_score = 0

        for cluster in clusters:
            cluster_words = set(cluster.cluster_name.lower().split())

            # Remove common words like "new:", punctuation
            cluster_words.discard("new:")

            if not cluster_words:
                continue

            overlap = len(issue_words & cluster_words)
            score = overlap / max(len(issue_words), 1)

            if score > self.SIMILARITY_THRESHOLD and score > best_score:
                best_match = cluster
                best_score = score

        return best_match

    async def _name_unnamed_clusters(self):
        """Use Claude to generate proper names for new clusters."""
        # Find clusters with temporary names (starting with "New:")
        result = await self.db.execute(
            select(IssueCluster).where(
                IssueCluster.cluster_name.like("New:%")
            )
        )
        unnamed_clusters = result.scalars().all()

        for cluster in unnamed_clusters:
            # Get issues in this cluster
            issues_result = await self.db.execute(
                select(ExtractedIssue).where(
                    ExtractedIssue.cluster_id == cluster.id
                ).limit(20)
            )
            issues = issues_result.scalars().all()

            # Only name clusters with 2+ issues
            if len(issues) >= 2:
                try:
                    issue_dicts = [
                        {
                            'category': i.category,
                            'subcategory': i.subcategory,
                            'summary': i.summary,
                            'representative_quote': i.representative_quote
                        }
                        for i in issues
                    ]

                    naming = self.analyzer.name_cluster(issue_dicts)
                    cluster.cluster_name = naming.get('cluster_name', cluster.cluster_name)
                    cluster.cluster_summary = naming.get('cluster_summary')

                except Exception as e:
                    logger.error(f"Error naming cluster {cluster.id}: {e}")
                    # Keep temporary name

        await self.db.commit()

    async def update_cluster_trends(self):
        """
        Calculate 7-day rolling trends for all active clusters.

        Compares issue counts from the last 7 days to the prior 7 days
        to calculate trend percentage.
        """
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        # Get all active clusters
        result = await self.db.execute(
            select(IssueCluster).where(IssueCluster.is_active == True)
        )
        clusters = result.scalars().all()

        for cluster in clusters:
            # Count issues in last 7 days
            count_7d_result = await self.db.execute(
                select(func.count(ExtractedIssue.id)).where(
                    ExtractedIssue.cluster_id == cluster.id,
                    ExtractedIssue.extracted_at >= week_ago
                )
            )
            count_7d = count_7d_result.scalar() or 0

            # Count issues in prior 7 days (days 8-14)
            count_prior_result = await self.db.execute(
                select(func.count(ExtractedIssue.id)).where(
                    ExtractedIssue.cluster_id == cluster.id,
                    ExtractedIssue.extracted_at >= two_weeks_ago,
                    ExtractedIssue.extracted_at < week_ago
                )
            )
            count_prior_7d = count_prior_result.scalar() or 0

            # Calculate trend percentage
            if count_prior_7d > 0:
                trend_pct = ((count_7d - count_prior_7d) / count_prior_7d) * 100
            else:
                trend_pct = 100 if count_7d > 0 else 0

            # Update cluster
            cluster.count_7d = count_7d
            cluster.count_prior_7d = count_prior_7d
            cluster.trend_pct = trend_pct
            cluster.updated_at = now

        await self.db.commit()
        logger.info(f"Updated trends for {len(clusters)} clusters")

    async def update_unique_customer_counts(self):
        """
        Count unique organizations per cluster.

        Uses the requester_org_name from tickets to count how many
        different customers are affected by each cluster.
        """
        result = await self.db.execute(
            select(IssueCluster).where(IssueCluster.is_active == True)
        )
        clusters = result.scalars().all()

        for cluster in clusters:
            # Count distinct organization names
            count_result = await self.db.execute(
                select(func.count(func.distinct(Ticket.requester_org_name)))
                .select_from(ExtractedIssue)
                .join(Ticket, ExtractedIssue.ticket_id == Ticket.id)
                .where(ExtractedIssue.cluster_id == cluster.id)
            )
            unique_customers = count_result.scalar() or 0
            cluster.unique_customers = unique_customers

        await self.db.commit()
        logger.info(f"Updated customer counts for {len(clusters)} clusters")

    async def merge_clusters(self, source_id: str, target_id: str) -> bool:
        """
        Merge one cluster into another.

        Moves all issues from the source cluster to the target cluster,
        deactivates the source cluster, and updates counts.

        Args:
            source_id: ID of cluster to merge from (will be deactivated)
            target_id: ID of cluster to merge into (will receive issues)

        Returns:
            True if merge was successful
        """
        # Move all issues from source to target
        await self.db.execute(
            update(ExtractedIssue)
            .where(ExtractedIssue.cluster_id == source_id)
            .values(cluster_id=target_id)
        )

        # Deactivate source cluster
        await self.db.execute(
            update(IssueCluster)
            .where(IssueCluster.id == source_id)
            .values(is_active=False)
        )

        # Update target cluster counts
        target_result = await self.db.execute(
            select(IssueCluster).where(IssueCluster.id == target_id)
        )
        target = target_result.scalar_one_or_none()

        if target:
            count_result = await self.db.execute(
                select(func.count(ExtractedIssue.id))
                .where(ExtractedIssue.cluster_id == target_id)
            )
            target.issue_count = count_result.scalar() or 0

        await self.db.commit()
        logger.info(f"Merged cluster {source_id} into {target_id}")
        return True


# Factory function
def get_clusterer(db: AsyncSession) -> ClusteringService:
    """
    Factory function to create a ClusteringService instance.

    Args:
        db: Async database session

    Returns:
        Configured ClusteringService instance
    """
    return ClusteringService(db)
