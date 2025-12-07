"""
Tests for API endpoints.

Tests cover:
- GET /api/issues with various filters
- GET /api/issues/summary
- GET /api/clusters
- GET /api/clusters/{id}
- PATCH /api/clusters/{id}
- Authentication requirements
- Pagination
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.models import Ticket, ExtractedIssue, IssueCluster


# Override database dependency for testing
async def override_get_db(db_session: AsyncSession):
    """Override get_db dependency with test session."""
    yield db_session


@pytest.mark.asyncio
@pytest.mark.api
class TestIssuesAPI:
    """Test suite for /api/issues endpoints."""

    async def test_list_issues_requires_auth(self, db_session: AsyncSession):
        """Test that listing issues requires authentication."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/issues")

        # Should return 401 without auth header
        assert response.status_code == 401

        app.dependency_overrides.clear()

    async def test_list_issues_success(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test successful listing of issues."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        # Create test data
        ticket = await create_ticket()
        await create_issue(
            ticket_id=ticket.id,
            summary="Test issue 1",
        )
        await create_issue(
            ticket_id=ticket.id,
            summary="Test issue 2",
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/issues", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        app.dependency_overrides.clear()

    async def test_list_issues_filter_by_category(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test filtering issues by category."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        ticket = await create_ticket()
        await create_issue(
            ticket_id=ticket.id,
            category="TIME_AND_ATTENDANCE",
            summary="T&A issue",
        )
        await create_issue(
            ticket_id=ticket.id,
            category="PAYROLL",
            summary="Payroll issue",
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"category": "PAYROLL"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "PAYROLL"

        app.dependency_overrides.clear()

    async def test_list_issues_filter_by_severity(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test filtering issues by severity."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        ticket = await create_ticket()
        await create_issue(ticket_id=ticket.id, severity="critical")
        await create_issue(ticket_id=ticket.id, severity="low")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"severity": "critical"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "critical"

        app.dependency_overrides.clear()

    async def test_list_issues_search(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test text search in issues."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        ticket = await create_ticket()
        await create_issue(ticket_id=ticket.id, summary="Geofencing clock-in error")
        await create_issue(ticket_id=ticket.id, summary="Tax calculation problem")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"search": "geofencing"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "geofencing" in data["items"][0]["summary"].lower()

        app.dependency_overrides.clear()

    async def test_list_issues_pagination(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test pagination of issues."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        # Create 25 issues
        ticket = await create_ticket()
        for i in range(25):
            await create_issue(ticket_id=ticket.id, summary=f"Issue {i}")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get first page (10 per page)
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"page": 1, "per_page": 10},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

        app.dependency_overrides.clear()

    async def test_get_issues_summary(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test getting issue summary statistics."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        # Create issues with different severities
        ticket = await create_ticket()
        await create_issue(ticket_id=ticket.id, severity="critical")
        await create_issue(ticket_id=ticket.id, severity="critical")
        await create_issue(ticket_id=ticket.id, severity="high")
        await create_issue(ticket_id=ticket.id, severity="medium")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues/summary",
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_issues_7d"] == 4
        assert data["critical_count"] == 2
        assert data["high_count"] == 1
        assert data["medium_count"] == 1
        assert data["low_count"] == 0

        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.api
class TestClustersAPI:
    """Test suite for /api/clusters endpoints."""

    async def test_list_clusters_requires_auth(self, db_session: AsyncSession):
        """Test that listing clusters requires authentication."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/clusters")

        assert response.status_code == 401

        app.dependency_overrides.clear()

    async def test_list_clusters_success(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test successful listing of clusters."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        await create_cluster(cluster_name="Cluster 1", issue_count=5)
        await create_cluster(cluster_name="Cluster 2", issue_count=3)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/clusters", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        app.dependency_overrides.clear()

    async def test_list_clusters_filter_by_category(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test filtering clusters by category."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        await create_cluster(category="TIME_AND_ATTENDANCE")
        await create_cluster(category="PAYROLL")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/clusters",
                headers=auth_header,
                params={"category": "PAYROLL"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "PAYROLL"

        app.dependency_overrides.clear()

    async def test_list_clusters_sort_by_issue_count(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test sorting clusters by issue count."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        await create_cluster(cluster_name="Small", issue_count=2)
        await create_cluster(cluster_name="Large", issue_count=10)
        await create_cluster(cluster_name="Medium", issue_count=5)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/clusters",
                headers=auth_header,
                params={"sort": "issue_count:desc"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["cluster_name"] == "Large"
        assert data["items"][1]["cluster_name"] == "Medium"
        assert data["items"][2]["cluster_name"] == "Small"

        app.dependency_overrides.clear()

    async def test_get_cluster_detail(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        sample_cluster_with_issues,
    ):
        """Test getting cluster detail with issues."""
        cluster, issues = sample_cluster_with_issues
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/clusters/{cluster.id}",
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(cluster.id)
        assert data["cluster_name"] == cluster.cluster_name
        assert len(data["issues"]) == 3
        assert len(data["tickets"]) == 2  # Should have 2 unique tickets

        app.dependency_overrides.clear()

    async def test_get_cluster_not_found(
        self, db_session: AsyncSession, auth_header: dict
    ):
        """Test getting non-existent cluster returns 404."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        from uuid import uuid4

        fake_id = uuid4()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/clusters/{fake_id}",
                headers=auth_header,
            )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    async def test_update_cluster_pm_status(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test updating cluster PM status."""
        cluster = await create_cluster(pm_status="new")
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.patch(
                f"/api/clusters/{cluster.id}",
                headers=auth_header,
                json={"pm_status": "reviewing"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pm_status"] == "reviewing"

        app.dependency_overrides.clear()

    async def test_update_cluster_pm_notes(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test updating cluster PM notes."""
        cluster = await create_cluster()
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.patch(
                f"/api/clusters/{cluster.id}",
                headers=auth_header,
                json={"pm_notes": "Investigating with engineering"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["pm_notes"] == "Investigating with engineering"

        app.dependency_overrides.clear()

    async def test_update_cluster_invalid_status(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_cluster,
    ):
        """Test updating cluster with invalid PM status."""
        cluster = await create_cluster()
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.patch(
                f"/api/clusters/{cluster.id}",
                headers=auth_header,
                json={"pm_status": "invalid_status"},
            )

        assert response.status_code == 400

        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.api
class TestAuthenticationAPI:
    """Test authentication requirements."""

    async def test_invalid_password_returns_401(
        self, db_session: AsyncSession, invalid_auth_header: dict
    ):
        """Test that invalid password returns 401."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/issues", headers=invalid_auth_header)

        assert response.status_code == 401

        app.dependency_overrides.clear()

    async def test_missing_auth_header_returns_401(self, db_session: AsyncSession):
        """Test that missing auth header returns 401."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/issues")

        assert response.status_code == 401

        app.dependency_overrides.clear()

    async def test_health_endpoint_no_auth(self):
        """Test that health endpoint doesn't require auth."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
@pytest.mark.api
class TestAPIEdgeCases:
    """Test edge cases and error handling."""

    async def test_list_issues_empty_results(
        self, db_session: AsyncSession, auth_header: dict
    ):
        """Test listing issues when none exist."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/issues", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

        app.dependency_overrides.clear()

    async def test_list_issues_filter_no_matches(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test filtering that returns no matches."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        ticket = await create_ticket()
        await create_issue(ticket_id=ticket.id, category="TIME_AND_ATTENDANCE")

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"search": "nonexistent_keyword_xyz"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

        app.dependency_overrides.clear()

    async def test_pagination_page_beyond_results(
        self,
        db_session: AsyncSession,
        auth_header: dict,
        create_ticket,
        create_issue,
    ):
        """Test requesting page beyond available results."""
        app.dependency_overrides[get_db] = lambda: override_get_db(db_session)

        ticket = await create_ticket()
        await create_issue(ticket_id=ticket.id)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/issues",
                headers=auth_header,
                params={"page": 100, "per_page": 10},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 1

        app.dependency_overrides.clear()
