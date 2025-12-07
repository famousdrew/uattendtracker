"""
SyncState model for tracking Zendesk sync progress.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncState(Base):
    """
    Tracks the state of the Zendesk sync process.

    Stores metadata about the last sync run including timestamps
    and counts of tickets and issues processed.
    """

    __tablename__ = "sync_state"

    # Primary key (serial for simplicity, only one row expected)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sync tracking
    last_ticket_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    tickets_synced: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0"
    )
    issues_extracted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0"
    )
    sync_completed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<SyncState(id={self.id}, "
            f"last_sync={self.sync_completed_at}, "
            f"tickets={self.tickets_synced}, "
            f"issues={self.issues_extracted})>"
        )
