"""
Ticket model for Zendesk support tickets.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    """
    Represents a Zendesk support ticket.

    Stores the raw ticket data synced from Zendesk along with
    metadata about when it was synced and analyzed.
    """

    __tablename__ = "tickets"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )

    # Zendesk ticket fields
    zendesk_ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    public_comments: Mapped[Optional[str]] = mapped_column(Text)
    requester_email: Mapped[Optional[str]] = mapped_column(String(255))
    requester_org_name: Mapped[Optional[str]] = mapped_column(String(255))
    zendesk_org_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    tags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    status: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[Optional[str]] = mapped_column(String(50))

    # Timestamp fields
    ticket_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ticket_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now()
    )
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )

    # Relationships
    issues: Mapped[List["ExtractedIssue"]] = relationship(
        "ExtractedIssue",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, zendesk_id={self.zendesk_ticket_id}, subject='{self.subject}')>"
