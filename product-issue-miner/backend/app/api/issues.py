"""
Issues API endpoints for listing, filtering, and analyzing product issues.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from typing import Optional, List
from datetime import date, datetime, timedelta
from uuid import UUID
import math

from app.api.deps import get_db, verify_password
from app.models import ExtractedIssue, Ticket
from app.schemas import (
    IssueResponse, IssueFilters, IssueSummary,
    PaginatedResponse, TrendDataPoint
)

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("", response_model=PaginatedResponse[IssueResponse])
async def list_issues(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    issue_type: Optional[str] = None,
    severity: Optional[str] = None,
    cluster_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    List issues with filtering and pagination.

    Supports filtering by:
    - category: Product category
    - subcategory: Product subcategory
    - issue_type: Type of issue (bug, friction, etc.)
    - severity: Severity level (critical, high, medium, low)
    - cluster_id: Issues in a specific cluster
    - start_date/end_date: Date range filter
    - search: Text search in summary and detail fields

    Returns paginated results sorted by extracted_at descending.
    """
    # Build base query
    query = select(ExtractedIssue)
    count_query = select(func.count()).select_from(ExtractedIssue)

    # Apply filters
    filters = []

    if category:
        filters.append(ExtractedIssue.category == category)

    if subcategory:
        filters.append(ExtractedIssue.subcategory == subcategory)

    if issue_type:
        filters.append(ExtractedIssue.issue_type == issue_type)

    if severity:
        filters.append(ExtractedIssue.severity == severity)

    if cluster_id:
        filters.append(ExtractedIssue.cluster_id == cluster_id)

    if start_date:
        filters.append(func.date(ExtractedIssue.extracted_at) >= start_date)

    if end_date:
        filters.append(func.date(ExtractedIssue.extracted_at) <= end_date)

    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                ExtractedIssue.summary.ilike(search_pattern),
                ExtractedIssue.detail.ilike(search_pattern)
            )
        )

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting and pagination
    query = query.order_by(ExtractedIssue.extracted_at.desc())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    issues = result.scalars().all()

    # Calculate total pages
    pages = math.ceil(total / per_page) if total > 0 else 0

    return PaginatedResponse(
        items=issues,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/summary", response_model=IssueSummary)
async def get_issues_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Get aggregated issue stats for dashboard.

    Returns:
    - Total issues in the last N days
    - Counts by severity level
    - Counts by category
    - Counts by issue type

    Args:
        days: Number of days to look back (default: 7, max: 90)
    """
    # Calculate date threshold
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query total count in period
    total_query = select(func.count()).select_from(ExtractedIssue).where(
        ExtractedIssue.extracted_at >= cutoff_date
    )
    total_result = await db.execute(total_query)
    total_issues = total_result.scalar_one()

    # Query counts by severity
    severity_query = (
        select(
            ExtractedIssue.severity,
            func.count().label('count')
        )
        .where(ExtractedIssue.extracted_at >= cutoff_date)
        .group_by(ExtractedIssue.severity)
    )
    severity_result = await db.execute(severity_query)
    severity_counts = {row.severity: row.count for row in severity_result}

    # Query counts by category
    category_query = (
        select(
            ExtractedIssue.category,
            func.count().label('count')
        )
        .where(ExtractedIssue.extracted_at >= cutoff_date)
        .group_by(ExtractedIssue.category)
        .order_by(func.count().desc())
    )
    category_result = await db.execute(category_query)
    by_category = [
        {"category": row.category, "count": row.count}
        for row in category_result
    ]

    # Query counts by issue_type
    issue_type_query = (
        select(
            ExtractedIssue.issue_type,
            func.count().label('count')
        )
        .where(ExtractedIssue.extracted_at >= cutoff_date)
        .group_by(ExtractedIssue.issue_type)
        .order_by(func.count().desc())
    )
    issue_type_result = await db.execute(issue_type_query)
    by_issue_type = [
        {"issue_type": row.issue_type, "count": row.count}
        for row in issue_type_result
    ]

    return IssueSummary(
        total_issues_7d=total_issues,
        critical_count=severity_counts.get('critical', 0),
        high_count=severity_counts.get('high', 0),
        medium_count=severity_counts.get('medium', 0),
        low_count=severity_counts.get('low', 0),
        by_category=by_category,
        by_issue_type=by_issue_type
    )


@router.get("/trends", response_model=List[TrendDataPoint])
async def get_issue_trends(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Get daily issue counts for trend chart.

    Returns a list of data points with date and count for each day
    in the specified period.

    Args:
        days: Number of days to include in trend (default: 30, max: 90)
    """
    # Calculate date threshold
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Query daily counts
    # Extract date part and count issues per day
    daily_query = (
        select(
            func.date(ExtractedIssue.extracted_at).label('date'),
            func.count().label('count')
        )
        .where(ExtractedIssue.extracted_at >= cutoff_date)
        .group_by(func.date(ExtractedIssue.extracted_at))
        .order_by(func.date(ExtractedIssue.extracted_at))
    )

    result = await db.execute(daily_query)
    rows = result.all()

    # Convert to TrendDataPoint format
    trend_data = [
        TrendDataPoint(
            date=row.date.isoformat(),
            count=row.count
        )
        for row in rows
    ]

    return trend_data
