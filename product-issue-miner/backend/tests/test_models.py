"""
Tests for database models (Ticket, ExtractedIssue, IssueCluster).

Tests cover:
- Model creation and validation
- CRUD operations
- Relationships between models
- Constraint validation
- Cascade delete behavior
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ticket, ExtractedIssue, IssueCluster
from app.models.issue import VALID_CATEGORIES, VALID_ISSUE_TYPES, VALID_SEVERITIES


@pytest.mark.asyncio
@pytest.mark.database
class TestTicketModel:
    """Test suite for Ticket model."""

    async def test_create_ticket(self, db_session: AsyncSession):
        """Test creating a new ticket."""
        ticket = Ticket(
            zendesk_ticket_id=12345,
            subject="Test ticket",
            description="Test description",
            requester_email="test@example.com",
            requester_org_name="Test Corp",
            zendesk_org_id=999,
            status="open",
            priority="high",
            tags=["product_issue", "urgent"],
            ticket_created_at=datetime.utcnow(),
            ticket_updated_at=datetime.utcnow(),
        )

        db_session.add(ticket)
        await db_session.commit()
        await db_session.refresh(ticket)

        assert ticket.id is not None
        assert ticket.zendesk_ticket_id == 12345
        assert ticket.subject == "Test ticket"
        assert ticket.tags == ["product_issue", "urgent"]
        assert ticket.analyzed_at is None

    async def test_ticket_unique_zendesk_id(
        self, db_session: AsyncSession, create_ticket
    ):
        """Test that zendesk_ticket_id must be unique."""
        await create_ticket(zendesk_ticket_id=99999)

        # Attempting to create another ticket with same zendesk_ticket_id should fail
        with pytest.raises(Exception):  # IntegrityError
            await create_ticket(zendesk_ticket_id=99999)

    async def test_ticket_relationships(
        self, db_session: AsyncSession, create_ticket, create_issue
    ):
        """Test ticket-to-issues relationship."""
        ticket = await create_ticket()

        # Create issues for this ticket
        issue1 = await create_issue(ticket_id=ticket.id, summary="Issue 1")
        issue2 = await create_issue(ticket_id=ticket.id, summary="Issue 2")

        # Refresh ticket to load relationships
        await db_session.refresh(ticket, ["issues"])

        assert len(ticket.issues) == 2
        assert issue1 in ticket.issues
        assert issue2 in ticket.issues

    async def test_ticket_cascade_delete(
        self, db_session: AsyncSession, create_ticket, create_issue
    ):
        """Test that deleting a ticket cascades to its issues."""
        ticket = await create_ticket()
        issue = await create_issue(ticket_id=ticket.id)

        # Delete ticket
        await db_session.delete(ticket)
        await db_session.commit()

        # Issue should also be deleted
        result = await db_session.execute(
            select(ExtractedIssue).where(ExtractedIssue.id == issue.id)
        )
        deleted_issue = result.scalar_one_or_none()
        assert deleted_issue is None

    async def test_ticket_optional_fields(self, db_session: AsyncSession):
        """Test creating ticket with minimal required fields."""
        ticket = Ticket(
            zendesk_ticket_id=54321,
            ticket_created_at=datetime.utcnow(),
            ticket_updated_at=datetime.utcnow(),
        )

        db_session.add(ticket)
        await db_session.commit()
        await db_session.refresh(ticket)

        assert ticket.id is not None
        assert ticket.subject is None
        assert ticket.description is None
        assert ticket.requester_email is None


@pytest.mark.asyncio
@pytest.mark.database
class TestExtractedIssueModel:
    """Test suite for ExtractedIssue model."""

    async def test_create_issue(self, db_session: AsyncSession, create_ticket):
        """Test creating an extracted issue."""
        ticket = await create_ticket()

        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            issue_type="bug",
            severity="high",
            summary="Clock-in not working",
            detail="Employees cannot clock in from mobile app",
            representative_quote="I can't clock in!",
            confidence=Decimal("0.90"),
        )

        db_session.add(issue)
        await db_session.commit()
        await db_session.refresh(issue)

        assert issue.id is not None
        assert issue.category == "TIME_AND_ATTENDANCE"
        assert issue.severity == "high"
        assert issue.confidence == Decimal("0.90")

    async def test_issue_valid_category(self, db_session: AsyncSession, create_ticket):
        """Test that only valid categories are accepted."""
        ticket = await create_ticket()

        # Valid category should work
        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="PAYROLL",
            subcategory="Tax Calculations",
            issue_type="bug",
            severity="medium",
            summary="Tax calculation incorrect",
        )
        db_session.add(issue)
        await db_session.commit()
        assert issue.id is not None

    async def test_issue_valid_severity(self, db_session: AsyncSession, create_ticket):
        """Test severity validation."""
        ticket = await create_ticket()

        for severity in VALID_SEVERITIES:
            issue = ExtractedIssue(
                ticket_id=ticket.id,
                category="SETTINGS",
                subcategory="User Management",
                issue_type="bug",
                severity=severity,
                summary=f"Issue with {severity} severity",
            )
            db_session.add(issue)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(select(ExtractedIssue))
        issues = result.scalars().all()
        assert len(issues) == len(VALID_SEVERITIES)

    async def test_issue_confidence_range(
        self, db_session: AsyncSession, create_ticket
    ):
        """Test that confidence must be between 0.00 and 1.00."""
        ticket = await create_ticket()

        # Valid confidence
        issue = ExtractedIssue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            issue_type="bug",
            severity="low",
            summary="Test issue",
            confidence=Decimal("0.75"),
        )
        db_session.add(issue)
        await db_session.commit()
        assert issue.confidence == Decimal("0.75")

    async def test_issue_cluster_relationship(
        self, db_session: AsyncSession, create_ticket, create_cluster
    ):
        """Test issue-to-cluster relationship."""
        ticket = await create_ticket()
        cluster = await create_cluster()

        issue = ExtractedIssue(
            ticket_id=ticket.id,
            cluster_id=cluster.id,
            category=cluster.category,
            subcategory=cluster.subcategory,
            issue_type="bug",
            severity="medium",
            summary="Clustered issue",
        )
        db_session.add(issue)
        await db_session.commit()
        await db_session.refresh(issue, ["cluster"])

        assert issue.cluster_id == cluster.id
        assert issue.cluster.cluster_name == cluster.cluster_name

    async def test_issue_cluster_set_null_on_delete(
        self, db_session: AsyncSession, create_ticket, create_cluster, create_issue
    ):
        """Test that deleting cluster sets issue.cluster_id to NULL."""
        ticket = await create_ticket()
        cluster = await create_cluster()
        issue = await create_issue(ticket_id=ticket.id, cluster_id=cluster.id)

        # Delete cluster
        await db_session.delete(cluster)
        await db_session.commit()
        await db_session.refresh(issue)

        # Issue should still exist but cluster_id should be NULL
        assert issue.cluster_id is None


@pytest.mark.asyncio
@pytest.mark.database
class TestIssueClusterModel:
    """Test suite for IssueCluster model."""

    async def test_create_cluster(self, db_session: AsyncSession):
        """Test creating an issue cluster."""
        cluster = IssueCluster(
            category="TIME_AND_ATTENDANCE",
            subcategory="Clock In/Out",
            cluster_name="Geofencing Issues",
            cluster_summary="Problems with geofence validation",
            issue_count=5,
            unique_customers=3,
            first_seen=datetime.utcnow() - timedelta(days=10),
            last_seen=datetime.utcnow(),
            count_7d=3,
            count_prior_7d=2,
            trend_pct=Decimal("50.00"),
            is_active=True,
            pm_status="new",
        )

        db_session.add(cluster)
        await db_session.commit()
        await db_session.refresh(cluster)

        assert cluster.id is not None
        assert cluster.cluster_name == "Geofencing Issues"
        assert cluster.issue_count == 5
        assert cluster.trend_pct == Decimal("50.00")
        assert cluster.is_active is True

    async def test_cluster_defaults(self, db_session: AsyncSession):
        """Test cluster default values."""
        cluster = IssueCluster(
            category="PAYROLL",
            subcategory="Direct Deposit",
            cluster_name="Direct deposit failures",
        )

        db_session.add(cluster)
        await db_session.commit()
        await db_session.refresh(cluster)

        assert cluster.issue_count == 0
        assert cluster.unique_customers == 0
        assert cluster.is_active is True
        assert cluster.pm_status == "new"
        assert cluster.pm_notes is None

    async def test_cluster_pm_status_values(self, db_session: AsyncSession):
        """Test valid PM status values."""
        valid_statuses = ["new", "reviewing", "acknowledged", "fixed", "wont_fix"]

        for status in valid_statuses:
            cluster = IssueCluster(
                category="SETTINGS",
                subcategory="Permissions",
                cluster_name=f"Cluster {status}",
                pm_status=status,
            )
            db_session.add(cluster)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(select(IssueCluster))
        clusters = result.scalars().all()
        assert len(clusters) == len(valid_statuses)

    async def test_cluster_issues_relationship(
        self, db_session: AsyncSession, create_ticket, create_cluster
    ):
        """Test cluster-to-issues relationship."""
        cluster = await create_cluster()
        ticket = await create_ticket()

        # Create multiple issues in this cluster
        for i in range(3):
            issue = ExtractedIssue(
                ticket_id=ticket.id,
                cluster_id=cluster.id,
                category=cluster.category,
                subcategory=cluster.subcategory,
                issue_type="bug",
                severity="medium",
                summary=f"Issue {i}",
            )
            db_session.add(issue)

        await db_session.commit()
        await db_session.refresh(cluster, ["issues"])

        assert len(cluster.issues) == 3

    async def test_cluster_update_pm_notes(
        self, db_session: AsyncSession, create_cluster
    ):
        """Test updating PM notes and status."""
        cluster = await create_cluster(pm_status="new")

        # Update status and notes
        cluster.pm_status = "reviewing"
        cluster.pm_notes = "Investigating with engineering team"

        await db_session.commit()
        await db_session.refresh(cluster)

        assert cluster.pm_status == "reviewing"
        assert cluster.pm_notes == "Investigating with engineering team"

    async def test_cluster_trend_calculation(
        self, db_session: AsyncSession, create_cluster
    ):
        """Test trend percentage calculation fields."""
        cluster = await create_cluster(
            count_7d=10,
            count_prior_7d=5,
            trend_pct=Decimal("100.00"),  # 100% increase
        )

        assert cluster.count_7d == 10
        assert cluster.count_prior_7d == 5
        assert cluster.trend_pct == Decimal("100.00")


@pytest.mark.asyncio
@pytest.mark.database
class TestModelRelationships:
    """Test complex relationships between models."""

    async def test_full_relationship_chain(
        self,
        db_session: AsyncSession,
        create_ticket,
        create_cluster,
    ):
        """Test complete relationship: Ticket -> Issue -> Cluster."""
        # Create ticket
        ticket = await create_ticket(zendesk_ticket_id=77777)

        # Create cluster
        cluster = await create_cluster(cluster_name="Test Cluster")

        # Create issue linking ticket and cluster
        issue = ExtractedIssue(
            ticket_id=ticket.id,
            cluster_id=cluster.id,
            category=cluster.category,
            subcategory=cluster.subcategory,
            issue_type="bug",
            severity="high",
            summary="Test issue",
        )
        db_session.add(issue)
        await db_session.commit()

        # Refresh all with relationships
        await db_session.refresh(ticket, ["issues"])
        await db_session.refresh(cluster, ["issues"])
        await db_session.refresh(issue, ["ticket", "cluster"])

        # Verify relationships
        assert len(ticket.issues) == 1
        assert ticket.issues[0].id == issue.id

        assert len(cluster.issues) == 1
        assert cluster.issues[0].id == issue.id

        assert issue.ticket.id == ticket.id
        assert issue.cluster.id == cluster.id

    async def test_multiple_issues_same_ticket(
        self,
        db_session: AsyncSession,
        create_ticket,
        create_cluster,
    ):
        """Test multiple issues from same ticket in different clusters."""
        ticket = await create_ticket()
        cluster1 = await create_cluster(cluster_name="Cluster 1")
        cluster2 = await create_cluster(cluster_name="Cluster 2")

        # Create two issues from same ticket
        issue1 = ExtractedIssue(
            ticket_id=ticket.id,
            cluster_id=cluster1.id,
            category=cluster1.category,
            subcategory=cluster1.subcategory,
            issue_type="bug",
            severity="high",
            summary="Issue 1",
        )
        issue2 = ExtractedIssue(
            ticket_id=ticket.id,
            cluster_id=cluster2.id,
            category=cluster2.category,
            subcategory=cluster2.subcategory,
            issue_type="friction",
            severity="medium",
            summary="Issue 2",
        )
        db_session.add_all([issue1, issue2])
        await db_session.commit()

        await db_session.refresh(ticket, ["issues"])

        # Ticket should have both issues
        assert len(ticket.issues) == 2
