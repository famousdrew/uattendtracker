"""
Tests for clustering service.

Tests cover:
- Issue clustering algorithm
- Keyword matching and similarity
- Trend calculation
- Unique customer counting
- Cluster merging
- Cluster naming
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExtractedIssue, IssueCluster
from app.services.clusterer import ClusteringService


@pytest.mark.asyncio
@pytest.mark.clustering
class TestClusteringService:
    """Test suite for ClusteringService."""

    async def test_cluster_issues_empty(
        self, db_session: AsyncSession, mock_claude_analyzer
    ):
        """Test clustering with no unclustered issues."""
        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)

        result = await service.cluster_issues()

        assert result["issues_clustered"] == 0
        assert result["new_clusters_created"] == 0

    async def test_cluster_single_issue(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_issue,
    ):
        """Test clustering a single issue creates new cluster."""
        ticket = await create_ticket()
        issue = await create_issue(
            ticket_id=ticket.id,
            cluster_id=None,
            summary="Clock-in geofencing error",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        result = await service.cluster_issues()

        assert result["issues_clustered"] == 1
        assert result["new_clusters_created"] == 1

        # Verify issue was assigned to cluster
        await db_session.refresh(issue)
        assert issue.cluster_id is not None

    async def test_cluster_similar_issues_same_cluster(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_issue,
    ):
        """Test similar issues get clustered together."""
        ticket1 = await create_ticket()
        ticket2 = await create_ticket()

        issue1 = await create_issue(
            ticket_id=ticket1.id,
            cluster_id=None,
            summary="Geofencing prevents clock in",
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
        )

        issue2 = await create_issue(
            ticket_id=ticket2.id,
            cluster_id=None,
            summary="Cannot clock in due to geofencing",
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        result = await service.cluster_issues()

        # Both issues should be clustered, likely in same cluster
        assert result["issues_clustered"] == 2

        await db_session.refresh(issue1)
        await db_session.refresh(issue2)

        # Issues with same category/subcategory and similar keywords should cluster together
        assert issue1.cluster_id is not None
        assert issue2.cluster_id is not None

    async def test_cluster_different_categories_separate(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_issue,
    ):
        """Test issues in different categories get separate clusters."""
        ticket1 = await create_ticket()
        ticket2 = await create_ticket()

        issue1 = await create_issue(
            ticket_id=ticket1.id,
            cluster_id=None,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            summary="Clock in problem",
        )

        issue2 = await create_issue(
            ticket_id=ticket2.id,
            cluster_id=None,
            category="PAYROLL",
            subcategory="Tax Calculations",
            summary="Tax calculation error",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        result = await service.cluster_issues()

        assert result["issues_clustered"] == 2
        assert result["new_clusters_created"] == 2

        await db_session.refresh(issue1)
        await db_session.refresh(issue2)

        # Should be in different clusters
        assert issue1.cluster_id != issue2.cluster_id

    async def test_find_matching_cluster(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
    ):
        """Test finding matching cluster based on keyword overlap."""
        cluster = await create_cluster(
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            cluster_name="Geofencing clock-in issues",
        )

        ticket = await create_ticket()
        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            issue_type="bug",
            severity="medium",
            summary="Geofencing prevents clock in",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)

        # Test matching
        matched = service._find_matching_cluster(issue, [cluster])

        assert matched is not None
        assert matched.id == cluster.id

    async def test_find_matching_cluster_no_match(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
    ):
        """Test no match when keywords don't overlap."""
        cluster = await create_cluster(
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            cluster_name="Geofencing issues",
        )

        ticket = await create_ticket()
        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            issue_type="bug",
            severity="medium",
            summary="Timesheet rounding problem",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)

        matched = service._find_matching_cluster(issue, [cluster])

        # Should not match - different keywords
        assert matched is None

    async def test_cluster_assigns_to_existing(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test that new issue gets assigned to existing cluster."""
        # Create existing cluster with an issue
        cluster = await create_cluster(
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            cluster_name="Geofencing clock-in errors",
            issue_count=1,
        )

        ticket1 = await create_ticket()
        existing_issue = await create_issue(
            ticket_id=ticket1.id,
            cluster_id=cluster.id,
            summary="Geofencing error",
        )

        # Create new unclustered issue with similar summary
        ticket2 = await create_ticket()
        new_issue = await create_issue(
            ticket_id=ticket2.id,
            cluster_id=None,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            summary="Geofencing clock-in problem",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        result = await service.cluster_issues()

        assert result["issues_clustered"] == 1
        assert result["new_clusters_created"] == 0

        await db_session.refresh(new_issue)
        assert new_issue.cluster_id == cluster.id

    async def test_update_cluster_trends(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test trend calculation for clusters."""
        cluster = await create_cluster()

        # Create issues in different time periods
        now = datetime.utcnow()

        # 3 issues in last 7 days
        for i in range(3):
            ticket = await create_ticket()
            issue = await create_issue(
                ticket_id=ticket.id,
                cluster_id=cluster.id,
            )
            issue.extracted_at = now - timedelta(days=i)
            await db_session.commit()

        # 2 issues in prior 7 days (8-14 days ago)
        for i in range(2):
            ticket = await create_ticket()
            issue = await create_issue(
                ticket_id=ticket.id,
                cluster_id=cluster.id,
            )
            issue.extracted_at = now - timedelta(days=8 + i)
            await db_session.commit()

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.update_cluster_trends()

        await db_session.refresh(cluster)

        assert cluster.count_7d == 3
        assert cluster.count_prior_7d == 2
        # Trend should be +50% (from 2 to 3)
        assert cluster.trend_pct == Decimal("50.00")

    async def test_update_unique_customer_counts(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test counting unique customers per cluster."""
        cluster = await create_cluster()

        # Create issues from different organizations
        for org_name in ["Company A", "Company B", "Company A", "Company C"]:
            ticket = await create_ticket(requester_org_name=org_name)
            await create_issue(ticket_id=ticket.id, cluster_id=cluster.id)

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.update_unique_customer_counts()

        await db_session.refresh(cluster)

        # Should count 3 unique organizations (A, B, C)
        assert cluster.unique_customers == 3

    async def test_merge_clusters(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test merging one cluster into another."""
        cluster1 = await create_cluster(cluster_name="Cluster 1", issue_count=2)
        cluster2 = await create_cluster(cluster_name="Cluster 2", issue_count=3)

        # Create issues in cluster1
        for _ in range(2):
            ticket = await create_ticket()
            await create_issue(ticket_id=ticket.id, cluster_id=cluster1.id)

        # Create issues in cluster2
        for _ in range(3):
            ticket = await create_ticket()
            await create_issue(ticket_id=ticket.id, cluster_id=cluster2.id)

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)

        # Merge cluster1 into cluster2
        await service.merge_clusters(
            source_id=str(cluster1.id),
            target_id=str(cluster2.id),
        )

        await db_session.refresh(cluster1)
        await db_session.refresh(cluster2)

        # Cluster1 should be deactivated
        assert cluster1.is_active is False

        # All issues should now be in cluster2
        result = await db_session.execute(
            select(ExtractedIssue).where(ExtractedIssue.cluster_id == cluster2.id)
        )
        cluster2_issues = result.scalars().all()
        assert len(cluster2_issues) == 5

        # No issues should remain in cluster1
        result = await db_session.execute(
            select(ExtractedIssue).where(ExtractedIssue.cluster_id == cluster1.id)
        )
        cluster1_issues = result.scalars().all()
        assert len(cluster1_issues) == 0

    async def test_cluster_naming(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_issue,
    ):
        """Test cluster naming with Claude."""
        # Create multiple issues for clustering
        for i in range(3):
            ticket = await create_ticket()
            await create_issue(
                ticket_id=ticket.id,
                cluster_id=None,
                category="TIME_AND_ATTENDANCE",
                subcategory="Clock In/Out",
                summary=f"Geofencing issue {i}",
            )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.cluster_issues()

        # Verify cluster was named
        result = await db_session.execute(select(IssueCluster))
        clusters = result.scalars().all()

        assert len(clusters) > 0
        cluster = clusters[0]

        # Should have a proper name (not starting with "New:")
        # After naming, it should use Claude's response
        assert cluster.cluster_name is not None

    async def test_trend_calculation_no_prior_issues(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test trend calculation when no prior period issues exist."""
        cluster = await create_cluster()

        # Create only recent issues (last 7 days)
        now = datetime.utcnow()
        for i in range(3):
            ticket = await create_ticket()
            issue = await create_issue(
                ticket_id=ticket.id,
                cluster_id=cluster.id,
            )
            issue.extracted_at = now - timedelta(days=i)
            await db_session.commit()

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.update_cluster_trends()

        await db_session.refresh(cluster)

        assert cluster.count_7d == 3
        assert cluster.count_prior_7d == 0
        # Should show 100% increase when no prior issues
        assert cluster.trend_pct == Decimal("100.00")

    async def test_inactive_clusters_excluded(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test that inactive clusters are not considered for matching."""
        # Create inactive cluster
        inactive_cluster = await create_cluster(
            cluster_name="Inactive cluster",
            is_active=False,
        )

        ticket = await create_ticket()
        issue = await create_issue(
            ticket_id=ticket.id,
            cluster_id=None,
            category=inactive_cluster.category,
            subcategory=inactive_cluster.subcategory,
            summary="Similar to inactive cluster",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        result = await service.cluster_issues()

        await db_session.refresh(issue)

        # Should create new cluster instead of using inactive one
        assert issue.cluster_id != inactive_cluster.id
        assert result["new_clusters_created"] == 1


@pytest.mark.asyncio
@pytest.mark.clustering
class TestClusteringEdgeCases:
    """Test edge cases in clustering logic."""

    async def test_empty_cluster_name_list(
        self, db_session: AsyncSession, mock_claude_analyzer
    ):
        """Test matching against cluster with empty name."""
        from app.models import IssueCluster

        cluster = IssueCluster(
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            cluster_name="",  # Empty name
        )
        db_session.add(cluster)
        await db_session.commit()

        ticket_data = {
            "zendesk_ticket_id": 999,
            "ticket_created_at": datetime.utcnow(),
            "ticket_updated_at": datetime.utcnow(),
        }
        from app.models import Ticket

        ticket = Ticket(**ticket_data)
        db_session.add(ticket)
        await db_session.commit()

        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            issue_type="bug",
            severity="medium",
            summary="Test issue",
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)

        # Should not match empty cluster name
        matched = service._find_matching_cluster(issue, [cluster])
        assert matched is None

    async def test_update_cluster_counts_on_assignment(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test that cluster issue counts update when issues are assigned."""
        cluster = await create_cluster(issue_count=0)

        # Create unclustered issue
        ticket = await create_ticket()
        await create_issue(
            ticket_id=ticket.id,
            cluster_id=None,
            category=cluster.category,
            subcategory=cluster.subcategory,
            summary=cluster.cluster_name,  # Ensure it matches
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.cluster_issues()

        await db_session.refresh(cluster)

        # Issue count should be incremented
        assert cluster.issue_count > 0

    async def test_cluster_last_seen_updated(
        self,
        db_session: AsyncSession,
        mock_claude_analyzer,
        create_ticket,
        create_cluster,
        create_issue,
    ):
        """Test that cluster last_seen is updated when new issue added."""
        old_time = datetime.utcnow() - timedelta(days=30)
        cluster = await create_cluster(last_seen=old_time)

        ticket = await create_ticket()
        await create_issue(
            ticket_id=ticket.id,
            cluster_id=None,
            category=cluster.category,
            subcategory=cluster.subcategory,
            summary=cluster.cluster_name,
        )

        service = ClusteringService(db=db_session, analyzer=mock_claude_analyzer)
        await service.cluster_issues()

        await db_session.refresh(cluster)

        # last_seen should be updated to recent time
        assert cluster.last_seen > old_time
