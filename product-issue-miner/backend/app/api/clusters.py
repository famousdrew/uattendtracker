"""
Clusters API endpoints for managing and viewing issue clusters.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List
from uuid import UUID
import math

from app.api.deps import get_db, verify_password
from app.models import IssueCluster, ExtractedIssue, Ticket
from app.schemas import (
    ClusterResponse, ClusterDetailResponse, ClusterUpdateRequest,
    ClusterFilters, PaginatedResponse, TicketListItem
)
from app.config import settings

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=PaginatedResponse[ClusterResponse])
async def list_clusters(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    is_active: Optional[bool] = True,
    pm_status: Optional[str] = None,
    sort: str = Query("issue_count:desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    List clusters with filtering and sorting.

    Supports filtering by:
    - category: Product category
    - subcategory: Product subcategory
    - is_active: Active status (default: True)
    - pm_status: PM status (new, reviewing, acknowledged, fixed, wont_fix)

    Supports sorting by:
    - issue_count:desc/asc (default)
    - unique_customers:desc/asc
    - last_seen:desc/asc
    - trend_pct:desc/asc

    Returns paginated results.
    """
    # Build base query
    query = select(IssueCluster)
    count_query = select(func.count()).select_from(IssueCluster)

    # Apply filters
    filters = []

    if category:
        filters.append(IssueCluster.category == category)

    if subcategory:
        filters.append(IssueCluster.subcategory == subcategory)

    if is_active is not None:
        filters.append(IssueCluster.is_active == is_active)

    if pm_status:
        filters.append(IssueCluster.pm_status == pm_status)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    sort_parts = sort.split(":")
    sort_field = sort_parts[0] if len(sort_parts) > 0 else "issue_count"
    sort_direction = sort_parts[1] if len(sort_parts) > 1 else "desc"

    # Map sort field to model attribute
    sort_column_map = {
        "issue_count": IssueCluster.issue_count,
        "unique_customers": IssueCluster.unique_customers,
        "last_seen": IssueCluster.last_seen,
        "trend_pct": IssueCluster.trend_pct,
        "created_at": IssueCluster.created_at,
    }

    sort_column = sort_column_map.get(sort_field, IssueCluster.issue_count)
    if sort_direction == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    clusters = result.scalars().all()

    # Calculate total pages
    pages = math.ceil(total / per_page) if total > 0 else 0

    return PaginatedResponse(
        items=clusters,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Get cluster detail with issues and tickets.

    Returns:
    - Cluster details and metrics
    - List of all issues in the cluster
    - List of unique tickets with Zendesk URLs

    Args:
        cluster_id: UUID of the cluster
    """
    # Fetch cluster with issues and their tickets
    query = (
        select(IssueCluster)
        .where(IssueCluster.id == cluster_id)
        .options(
            selectinload(IssueCluster.issues).selectinload(ExtractedIssue.ticket)
        )
    )

    result = await db.execute(query)
    cluster = result.scalar_one_or_none()

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Build list of unique tickets with Zendesk URLs
    seen_ticket_ids = set()
    tickets_list = []

    for issue in cluster.issues:
        ticket = issue.ticket
        if ticket.id not in seen_ticket_ids:
            seen_ticket_ids.add(ticket.id)

            # Construct Zendesk URL
            zendesk_url = f"https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/{ticket.zendesk_ticket_id}"

            # Find highest severity from issues on this ticket in this cluster
            issue_severities = [i.severity for i in cluster.issues if i.ticket_id == ticket.id]
            severity_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            highest_severity = min(issue_severities, key=lambda s: severity_priority.get(s, 999)) if issue_severities else None

            ticket_item = TicketListItem(
                zendesk_ticket_id=ticket.zendesk_ticket_id,
                subject=ticket.subject,
                requester_org_name=ticket.requester_org_name,
                ticket_created_at=ticket.ticket_created_at,
                severity=highest_severity,
                zendesk_url=zendesk_url
            )
            tickets_list.append(ticket_item)

    # Sort tickets by created_at descending
    tickets_list.sort(key=lambda t: t.ticket_created_at, reverse=True)

    # Create response
    return ClusterDetailResponse(
        id=cluster.id,
        category=cluster.category,
        subcategory=cluster.subcategory,
        cluster_name=cluster.cluster_name,
        cluster_summary=cluster.cluster_summary,
        issue_count=cluster.issue_count,
        unique_customers=cluster.unique_customers,
        first_seen=cluster.first_seen,
        last_seen=cluster.last_seen,
        count_7d=cluster.count_7d,
        count_prior_7d=cluster.count_prior_7d,
        trend_pct=cluster.trend_pct,
        is_active=cluster.is_active,
        pm_status=cluster.pm_status,
        pm_notes=cluster.pm_notes,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
        issues=cluster.issues,
        tickets=tickets_list
    )


@router.patch("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: UUID,
    update: ClusterUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Update cluster PM status and notes.

    Allows PM teams to update:
    - pm_status: new, reviewing, acknowledged, fixed, wont_fix
    - pm_notes: Free-text notes about the cluster

    Args:
        cluster_id: UUID of the cluster
        update: Update request body
    """
    # Fetch cluster
    query = select(IssueCluster).where(IssueCluster.id == cluster_id)
    result = await db.execute(query)
    cluster = result.scalar_one_or_none()

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Update fields if provided
    if update.pm_status is not None:
        # Validate pm_status
        valid_statuses = ["new", "reviewing", "acknowledged", "fixed", "wont_fix"]
        if update.pm_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pm_status. Must be one of: {', '.join(valid_statuses)}"
            )
        cluster.pm_status = update.pm_status

    if update.pm_notes is not None:
        cluster.pm_notes = update.pm_notes

    # Commit changes
    await db.commit()
    await db.refresh(cluster)

    return cluster
