"""
Export API endpoints for downloading data as CSV files.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import csv
import io
from typing import Optional
from datetime import date
from uuid import UUID

from app.api.deps import get_db, verify_password
from app.models import ExtractedIssue, IssueCluster, Ticket
from app.config import settings

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/issues")
async def export_issues(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Export issues as CSV.

    Returns a CSV file with all issue data matching the filters.

    Filters:
    - category: Product category
    - severity: Severity level
    - start_date/end_date: Date range

    CSV columns:
    - Issue ID, Ticket ID, Zendesk Ticket ID, Category, Subcategory,
      Issue Type, Severity, Summary, Detail, Representative Quote,
      Confidence, Extracted At, Cluster ID
    """
    # Build query
    query = select(ExtractedIssue).options(selectinload(ExtractedIssue.ticket))

    # Apply filters
    filters = []

    if category:
        filters.append(ExtractedIssue.category == category)

    if severity:
        filters.append(ExtractedIssue.severity == severity)

    if start_date:
        from sqlalchemy import func
        filters.append(func.date(ExtractedIssue.extracted_at) >= start_date)

    if end_date:
        from sqlalchemy import func
        filters.append(func.date(ExtractedIssue.extracted_at) <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Order by extracted_at
    query = query.order_by(ExtractedIssue.extracted_at.desc())

    # Execute query
    result = await db.execute(query)
    issues = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Issue ID',
        'Ticket ID',
        'Zendesk Ticket ID',
        'Zendesk URL',
        'Category',
        'Subcategory',
        'Issue Type',
        'Severity',
        'Summary',
        'Detail',
        'Representative Quote',
        'Confidence',
        'Extracted At',
        'Cluster ID',
        'Requester Email',
        'Requester Org'
    ])

    # Write data rows
    for issue in issues:
        zendesk_url = f"https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/{issue.ticket.zendesk_ticket_id}"

        writer.writerow([
            str(issue.id),
            str(issue.ticket_id),
            issue.ticket.zendesk_ticket_id,
            zendesk_url,
            issue.category,
            issue.subcategory,
            issue.issue_type,
            issue.severity,
            issue.summary,
            issue.detail or '',
            issue.representative_quote or '',
            float(issue.confidence) if issue.confidence else '',
            issue.extracted_at.isoformat(),
            str(issue.cluster_id) if issue.cluster_id else '',
            issue.ticket.requester_email or '',
            issue.ticket.requester_org_name or ''
        ])

    # Prepare streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=issues_export_{date.today().isoformat()}.csv"
        }
    )


@router.get("/clusters")
async def export_clusters(
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Export clusters as CSV.

    Returns a CSV file with cluster data matching the filters.

    Filters:
    - category: Product category
    - is_active: Active status (default: True)

    CSV columns:
    - Cluster ID, Category, Subcategory, Cluster Name, Cluster Summary,
      Issue Count, Unique Customers, First Seen, Last Seen, Count 7d,
      Count Prior 7d, Trend %, Is Active, PM Status, PM Notes,
      Created At, Updated At
    """
    # Build query
    query = select(IssueCluster)

    # Apply filters
    filters = []

    if category:
        filters.append(IssueCluster.category == category)

    if is_active is not None:
        filters.append(IssueCluster.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))

    # Order by issue_count descending
    query = query.order_by(IssueCluster.issue_count.desc())

    # Execute query
    result = await db.execute(query)
    clusters = result.scalars().all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Cluster ID',
        'Category',
        'Subcategory',
        'Cluster Name',
        'Cluster Summary',
        'Issue Count',
        'Unique Customers',
        'First Seen',
        'Last Seen',
        'Count 7d',
        'Count Prior 7d',
        'Trend %',
        'Is Active',
        'PM Status',
        'PM Notes',
        'Created At',
        'Updated At'
    ])

    # Write data rows
    for cluster in clusters:
        writer.writerow([
            str(cluster.id),
            cluster.category,
            cluster.subcategory,
            cluster.cluster_name,
            cluster.cluster_summary or '',
            cluster.issue_count,
            cluster.unique_customers,
            cluster.first_seen.isoformat() if cluster.first_seen else '',
            cluster.last_seen.isoformat() if cluster.last_seen else '',
            cluster.count_7d,
            cluster.count_prior_7d,
            float(cluster.trend_pct) if cluster.trend_pct else '',
            cluster.is_active,
            cluster.pm_status,
            cluster.pm_notes or '',
            cluster.created_at.isoformat(),
            cluster.updated_at.isoformat()
        ])

    # Prepare streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=clusters_export_{date.today().isoformat()}.csv"
        }
    )
