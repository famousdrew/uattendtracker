"""
Pytest fixtures and configuration for Product Issue Miner tests.

This module provides shared fixtures for:
- Test database setup/teardown with async support
- Mock Zendesk client for API testing
- Mock Claude analyzer for AI-powered testing
- Test authentication headers
- Sample data factories
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from faker import Faker

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.database import Base
from app.models import Ticket, ExtractedIssue, IssueCluster, SyncState
from app.services.zendesk import ZendeskClient
from app.services.analyzer import IssueAnalyzer

# Initialize Faker for generating test data
fake = Faker()


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test database URL (use SQLite for simplicity, or set TEST_DATABASE_URL in env)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create test database engine with in-memory SQLite.

    Each test gets a fresh database instance.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session.

    Provides a clean database session for each test with automatic rollback.
    """
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# Mock Zendesk Client fixtures
@pytest.fixture
def mock_zendesk_client() -> MagicMock:
    """
    Create mock Zendesk client for testing.

    Returns a MagicMock configured with common Zendesk API responses.
    """
    mock_client = MagicMock(spec=ZendeskClient)

    # Configure mock methods as async
    mock_client.get_ticket = AsyncMock()
    mock_client.get_ticket_comments = AsyncMock()
    mock_client.get_ticket_with_comments = AsyncMock()
    mock_client.search_tickets = AsyncMock()
    mock_client.paginate_search = AsyncMock()
    mock_client.get_user = AsyncMock()
    mock_client.get_organization = AsyncMock()
    mock_client.format_comments = MagicMock()
    mock_client.close = AsyncMock()

    # Default return values
    mock_client.format_comments.return_value = "Formatted comments"

    return mock_client


@pytest.fixture
def sample_zendesk_ticket() -> dict:
    """Sample Zendesk ticket data for testing."""
    return {
        "id": 12345,
        "subject": "Unable to clock in - time and attendance issue",
        "description": "Employee reports error when trying to clock in",
        "status": "open",
        "priority": "high",
        "tags": ["product_issue", "time_attendance"],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T14:22:00Z",
        "requester_id": 67890,
        "organization_id": 11111,
    }


@pytest.fixture
def sample_zendesk_comments() -> list:
    """Sample Zendesk comments for testing."""
    return [
        {
            "id": 1,
            "author_id": 67890,
            "body": "I'm getting an error message when I try to clock in.",
            "plain_body": "I'm getting an error message when I try to clock in.",
            "public": True,
            "created_at": "2024-01-15T10:30:00Z",
        },
        {
            "id": 2,
            "author_id": 99999,
            "body": "This appears to be a geofencing issue. Investigating.",
            "plain_body": "This appears to be a geofencing issue. Investigating.",
            "public": False,
            "created_at": "2024-01-15T11:00:00Z",
        },
    ]


@pytest.fixture
def sample_ticket_with_comments(
    sample_zendesk_ticket, sample_zendesk_comments
) -> dict:
    """Complete ticket data with comments for testing."""
    public_comments = [c for c in sample_zendesk_comments if c.get("public")]
    internal_notes = [c for c in sample_zendesk_comments if not c.get("public")]

    return {
        "ticket": sample_zendesk_ticket,
        "all_comments": sample_zendesk_comments,
        "public_comments": public_comments,
        "internal_notes": internal_notes,
    }


# Mock Claude Analyzer fixtures
@pytest.fixture
def mock_claude_analyzer() -> MagicMock:
    """
    Create mock Claude analyzer for testing.

    Returns a MagicMock configured with sample issue extraction responses.
    """
    mock_analyzer = MagicMock(spec=IssueAnalyzer)

    # Configure extract_issues to return sample issues
    mock_analyzer.extract_issues.return_value = {
        "issues": [
            {
                "category": "TIME_AND_ATTENDANCE",
                "subcategory": "Clock In/Out",
                "issue_type": "bug",
                "severity": "high",
                "summary": "Geofencing prevents valid clock-in attempts",
                "detail": "Employees within valid location unable to clock in due to geofencing errors",
                "representative_quote": "I'm getting an error message when I try to clock in.",
                "confidence": 0.85,
            }
        ],
        "no_product_issue": False,
        "skip_reason": None,
    }

    # Configure name_cluster to return sample cluster names
    mock_analyzer.name_cluster.return_value = {
        "cluster_name": "Geofencing Clock-In Errors",
        "cluster_summary": "Multiple employees reporting inability to clock in due to geofencing validation failures",
    }

    return mock_analyzer


@pytest.fixture
def sample_extracted_issue_data() -> dict:
    """Sample extracted issue data for creating test issues."""
    return {
        "category": "TIME_AND_ATTENDANCE",
        "subcategory": "Clock In/Out",
        "issue_type": "bug",
        "severity": "high",
        "summary": "Geofencing prevents valid clock-in attempts",
        "detail": "Employees within valid location unable to clock in",
        "representative_quote": "I'm getting an error message",
        "confidence": Decimal("0.85"),
    }


# Database model factory fixtures
@pytest_asyncio.fixture
async def create_ticket(db_session: AsyncSession):
    """
    Factory fixture for creating test tickets.

    Returns a function that creates and persists a Ticket.
    """
    async def _create_ticket(**kwargs) -> Ticket:
        defaults = {
            "zendesk_ticket_id": fake.random_int(min=10000, max=99999),
            "subject": fake.sentence(),
            "description": fake.text(max_nb_chars=200),
            "internal_notes": "Internal note: " + fake.sentence(),
            "public_comments": "Customer: " + fake.sentence(),
            "requester_email": fake.email(),
            "requester_org_name": fake.company(),
            "zendesk_org_id": fake.random_int(min=1000, max=9999),
            "tags": ["product_issue"],
            "status": "open",
            "priority": "normal",
            "ticket_created_at": datetime.utcnow() - timedelta(days=7),
            "ticket_updated_at": datetime.utcnow() - timedelta(days=1),
        }
        defaults.update(kwargs)

        ticket = Ticket(**defaults)
        db_session.add(ticket)
        await db_session.commit()
        await db_session.refresh(ticket)
        return ticket

    return _create_ticket


@pytest_asyncio.fixture
async def create_issue(db_session: AsyncSession):
    """
    Factory fixture for creating test issues.

    Returns a function that creates and persists an ExtractedIssue.
    """
    async def _create_issue(ticket_id, **kwargs) -> ExtractedIssue:
        defaults = {
            "ticket_id": ticket_id,
            "category": "TIME_AND_ATTENDANCE",
            "subcategory": "Clock In/Out",
            "issue_type": "bug",
            "severity": "medium",
            "summary": fake.sentence(),
            "detail": fake.text(max_nb_chars=100),
            "representative_quote": fake.sentence(),
            "confidence": Decimal("0.80"),
        }
        defaults.update(kwargs)

        issue = ExtractedIssue(**defaults)
        db_session.add(issue)
        await db_session.commit()
        await db_session.refresh(issue)
        return issue

    return _create_issue


@pytest_asyncio.fixture
async def create_cluster(db_session: AsyncSession):
    """
    Factory fixture for creating test clusters.

    Returns a function that creates and persists an IssueCluster.
    """
    async def _create_cluster(**kwargs) -> IssueCluster:
        defaults = {
            "category": "TIME_AND_ATTENDANCE",
            "subcategory": "Clock In/Out",
            "cluster_name": fake.sentence(nb_words=4),
            "cluster_summary": fake.text(max_nb_chars=100),
            "issue_count": 0,
            "unique_customers": 0,
            "first_seen": datetime.utcnow() - timedelta(days=30),
            "last_seen": datetime.utcnow(),
            "count_7d": 0,
            "count_prior_7d": 0,
            "trend_pct": Decimal("0.00"),
            "is_active": True,
            "pm_status": "new",
        }
        defaults.update(kwargs)

        cluster = IssueCluster(**defaults)
        db_session.add(cluster)
        await db_session.commit()
        await db_session.refresh(cluster)
        return cluster

    return _create_cluster


# Authentication fixtures
@pytest.fixture
def auth_header() -> dict:
    """Test authentication header for API tests."""
    return {"X-Dashboard-Password": "test_password"}


@pytest.fixture
def invalid_auth_header() -> dict:
    """Invalid authentication header for testing auth failures."""
    return {"X-Dashboard-Password": "wrong_password"}


# Sample data fixtures for complex scenarios
@pytest_asyncio.fixture
async def sample_ticket_with_issues(
    db_session: AsyncSession,
    create_ticket,
    create_issue,
) -> tuple[Ticket, list[ExtractedIssue]]:
    """
    Create a sample ticket with multiple issues for testing.

    Returns tuple of (ticket, issues).
    """
    ticket = await create_ticket(
        subject="Multiple issues in time tracking",
        zendesk_ticket_id=11111,
    )

    issue1 = await create_issue(
        ticket_id=ticket.id,
        summary="Clock-in geofencing error",
        severity="high",
    )

    issue2 = await create_issue(
        ticket_id=ticket.id,
        summary="Time entry rounding confusion",
        severity="low",
        issue_type="ux_confusion",
    )

    return ticket, [issue1, issue2]


@pytest_asyncio.fixture
async def sample_cluster_with_issues(
    db_session: AsyncSession,
    create_ticket,
    create_issue,
    create_cluster,
) -> tuple[IssueCluster, list[ExtractedIssue]]:
    """
    Create a sample cluster with multiple issues for testing.

    Returns tuple of (cluster, issues).
    """
    cluster = await create_cluster(
        cluster_name="Geofencing Issues",
        issue_count=3,
        unique_customers=2,
    )

    # Create tickets and issues
    ticket1 = await create_ticket(
        requester_org_name="Company A",
        zendesk_ticket_id=22222,
    )
    ticket2 = await create_ticket(
        requester_org_name="Company B",
        zendesk_ticket_id=33333,
    )

    issue1 = await create_issue(
        ticket_id=ticket1.id,
        cluster_id=cluster.id,
        summary="Geofencing clock-in blocked",
    )
    issue2 = await create_issue(
        ticket_id=ticket1.id,
        cluster_id=cluster.id,
        summary="Geofencing too strict",
    )
    issue3 = await create_issue(
        ticket_id=ticket2.id,
        cluster_id=cluster.id,
        summary="Can't clock in from valid location",
    )

    return cluster, [issue1, issue2, issue3]
