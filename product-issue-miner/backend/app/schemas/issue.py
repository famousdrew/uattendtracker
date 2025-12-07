from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date
from uuid import UUID
from enum import Enum

if TYPE_CHECKING:
    from app.schemas.ticket import TicketListItem

class CategoryEnum(str, Enum):
    TIME_AND_ATTENDANCE = "TIME_AND_ATTENDANCE"
    PAYROLL = "PAYROLL"
    SETTINGS = "SETTINGS"

class SeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class IssueTypeEnum(str, Enum):
    BUG = "bug"
    FRICTION = "friction"
    UX_CONFUSION = "ux_confusion"
    FEATURE_REQUEST = "feature_request"
    DOCUMENTATION_GAP = "documentation_gap"
    DATA_ISSUE = "data_issue"

class IssueBase(BaseModel):
    category: str
    subcategory: str
    issue_type: str
    severity: str
    summary: str
    detail: Optional[str] = None
    representative_quote: Optional[str] = None
    confidence: Optional[float] = None

class IssueResponse(IssueBase):
    id: UUID
    ticket_id: UUID
    cluster_id: Optional[UUID] = None
    extracted_at: datetime

    class Config:
        from_attributes = True

class IssueWithTicket(IssueResponse):
    """Issue with nested ticket info."""
    ticket: "TicketListItem"

class IssueFilters(BaseModel):
    """Query parameters for filtering issues."""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    issue_type: Optional[str] = None
    severity: Optional[str] = None  # Comma-separated for multiple
    cluster_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)

class IssueSummary(BaseModel):
    """Aggregated issue stats for dashboard."""
    total_issues_7d: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    by_category: List[dict]  # [{category: str, count: int}]
    by_issue_type: List[dict]  # [{issue_type: str, count: int}]

class TrendDataPoint(BaseModel):
    """Single data point for trend chart."""
    date: str  # ISO date string
    count: int
