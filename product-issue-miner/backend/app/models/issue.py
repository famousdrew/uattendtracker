"""
ExtractedIssue model for product issues extracted from tickets.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Valid values for check constraints
VALID_CATEGORIES = ["TIME_AND_ATTENDANCE", "PAYROLL", "SETTINGS"]
VALID_ISSUE_TYPES = [
    "bug",
    "friction",
    "ux_confusion",
    "feature_request",
    "documentation_gap",
    "data_issue",
]
VALID_SEVERITIES = ["critical", "high", "medium", "low"]


class ExtractedIssue(Base):
    """
    Represents a product issue extracted from a support ticket.

    Each ticket can have multiple issues. Issues are categorized,
    classified by type and severity, and can be grouped into clusters.
    """

    __tablename__ = "extracted_issues"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )

    # Foreign keys
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )
    cluster_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issue_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Classification fields
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
    issue_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # Issue details
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    representative_quote: Mapped[Optional[str]] = mapped_column(Text)

    # Confidence score (0.00 to 1.00)
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )

    # Timestamp
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="issues"
    )
    cluster: Mapped[Optional["IssueCluster"]] = relationship(
        "IssueCluster",
        back_populates="issues"
    )

    # Check constraints for valid enum values
    __table_args__ = (
        CheckConstraint(
            f"category IN ({', '.join(repr(c) for c in VALID_CATEGORIES)})",
            name="check_valid_category"
        ),
        CheckConstraint(
            f"issue_type IN ({', '.join(repr(t) for t in VALID_ISSUE_TYPES)})",
            name="check_valid_issue_type"
        ),
        CheckConstraint(
            f"severity IN ({', '.join(repr(s) for s in VALID_SEVERITIES)})",
            name="check_valid_severity"
        ),
        CheckConstraint(
            "confidence >= 0.00 AND confidence <= 1.00",
            name="check_confidence_range"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ExtractedIssue(id={self.id}, "
            f"category={self.category}, "
            f"severity={self.severity}, "
            f"summary='{self.summary[:50]}...')>"
        )
