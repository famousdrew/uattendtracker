from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID

if TYPE_CHECKING:
    from app.schemas.issue import IssueResponse

class TicketBase(BaseModel):
    zendesk_ticket_id: int
    subject: Optional[str] = None
    requester_email: Optional[str] = None
    requester_org_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    ticket_created_at: datetime
    ticket_updated_at: datetime

class TicketResponse(TicketBase):
    id: UUID
    synced_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TicketDetailResponse(TicketResponse):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    issues: List["IssueResponse"] = []
    zendesk_url: str  # Constructed URL to Zendesk ticket

class TicketListItem(BaseModel):
    """Minimal ticket info for cluster detail views."""
    zendesk_ticket_id: int
    subject: Optional[str] = None
    requester_org_name: Optional[str] = None
    ticket_created_at: datetime
    severity: Optional[str] = None
    zendesk_url: str

    class Config:
        from_attributes = True
