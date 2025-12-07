"""
IssueCluster model for grouping similar product issues.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Valid PM statuses
VALID_PM_STATUSES = ["new", "reviewing", "acknowledged", "fixed", "wont_fix"]


class IssueCluster(Base):
    """
    Represents a cluster of similar product issues.

    Issues are grouped into clusters based on similarity. Clusters
    track metrics like issue count, customer count, and trends over time.
    PM teams can track the status and add notes to clusters.
    """

    __tablename__ = "issue_clusters"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )

    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    subcategory: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    # Cluster details
    cluster_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cluster_summary: Mapped[Optional[str]] = mapped_column(Text)

    # Metrics
    issue_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    unique_customers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0"
    )

    # Time tracking
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Trend analysis (last 7 days vs prior 7 days)
    count_7d: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    count_prior_7d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0"
    )
    trend_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Status tracking
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        index=True
    )
    pm_status: Mapped[str] = mapped_column(
        String(50),
        default="new",
        server_default="'new'"
    )
    pm_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow
    )

    # Relationships
    issues: Mapped[List["ExtractedIssue"]] = relationship(
        "ExtractedIssue",
        back_populates="cluster"
    )

    # Check constraint for valid PM status
    __table_args__ = (
        CheckConstraint(
            f"pm_status IN ({', '.join(repr(s) for s in VALID_PM_STATUSES)})",
            name="check_valid_pm_status"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<IssueCluster(id={self.id}, "
            f"name='{self.cluster_name}', "
            f"count={self.issue_count}, "
            f"status={self.pm_status})>"
        )
