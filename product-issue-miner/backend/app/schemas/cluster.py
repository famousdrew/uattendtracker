from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from enum import Enum

if TYPE_CHECKING:
    from app.schemas.issue import IssueResponse
    from app.schemas.ticket import TicketListItem

class PMStatusEnum(str, Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    ACKNOWLEDGED = "acknowledged"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"

class ClusterBase(BaseModel):
    category: str
    subcategory: str
    cluster_name: str
    cluster_summary: Optional[str] = None

class ClusterResponse(ClusterBase):
    id: UUID
    issue_count: int
    unique_customers: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    count_7d: int
    count_prior_7d: int
    trend_pct: Optional[float] = None
    is_active: bool
    pm_status: str
    pm_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClusterListResponse(ClusterResponse):
    """Cluster for list views - same as ClusterResponse."""
    pass

class ClusterDetailResponse(ClusterResponse):
    """Cluster with associated issues and tickets."""
    issues: List["IssueResponse"] = []
    tickets: List["TicketListItem"] = []

class ClusterUpdateRequest(BaseModel):
    """Request body for updating cluster PM fields."""
    pm_status: Optional[str] = None
    pm_notes: Optional[str] = None

class ClusterFilters(BaseModel):
    """Query parameters for filtering clusters."""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_active: Optional[bool] = True
    pm_status: Optional[str] = None
    sort: str = Field(default="issue_count:desc")  # field:direction
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
