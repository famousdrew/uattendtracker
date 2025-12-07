"""
Tickets API endpoints for viewing ticket details and extracted issues.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, verify_password
from app.models import Ticket
from app.schemas import TicketDetailResponse
from app.config import settings

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/{zendesk_id}", response_model=TicketDetailResponse)
async def get_ticket(
    zendesk_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Get single ticket with all extracted issues.

    Returns complete ticket information including:
    - Ticket metadata (subject, status, requester, etc.)
    - All extracted issues for this ticket
    - Zendesk URL for accessing the ticket in Zendesk

    Args:
        zendesk_id: Zendesk ticket ID
    """
    # Fetch ticket with issues
    query = (
        select(Ticket)
        .where(Ticket.zendesk_ticket_id == zendesk_id)
        .options(selectinload(Ticket.issues))
    )

    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Construct Zendesk URL
    zendesk_url = f"https://{settings.ZENDESK_SUBDOMAIN}.zendesk.com/agent/tickets/{ticket.zendesk_ticket_id}"

    # Create response
    return TicketDetailResponse(
        id=ticket.id,
        zendesk_ticket_id=ticket.zendesk_ticket_id,
        subject=ticket.subject,
        description=ticket.description,
        requester_email=ticket.requester_email,
        requester_org_name=ticket.requester_org_name,
        status=ticket.status,
        priority=ticket.priority,
        ticket_created_at=ticket.ticket_created_at,
        ticket_updated_at=ticket.ticket_updated_at,
        synced_at=ticket.synced_at,
        analyzed_at=ticket.analyzed_at,
        tags=ticket.tags if ticket.tags else [],
        issues=ticket.issues,
        zendesk_url=zendesk_url
    )
