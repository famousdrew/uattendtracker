"""Simple SQLite storage for MVP."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class Storage:
    """SQLite-based storage for tickets and issues."""

    def __init__(self, db_path: str = "mvp_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY,
                    zendesk_id INTEGER UNIQUE NOT NULL,
                    subject TEXT,
                    description TEXT,
                    comments_json TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    requester_email TEXT,
                    tags TEXT,
                    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    category TEXT,
                    issue_type TEXT,
                    severity TEXT,
                    summary TEXT,
                    detail TEXT,
                    confidence REAL,
                    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(zendesk_id)
                );

                CREATE INDEX IF NOT EXISTS idx_tickets_zendesk_id ON tickets(zendesk_id);
                CREATE INDEX IF NOT EXISTS idx_issues_ticket_id ON issues(ticket_id);
                CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
                CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity);
            """)

    def upsert_ticket(self, ticket: dict, comments: list[dict] = None):
        """Insert or update a ticket."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tickets (zendesk_id, subject, description, comments_json, status,
                                     created_at, updated_at, requester_email, tags, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(zendesk_id) DO UPDATE SET
                    subject = excluded.subject,
                    description = excluded.description,
                    comments_json = excluded.comments_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    requester_email = excluded.requester_email,
                    tags = excluded.tags,
                    synced_at = excluded.synced_at
            """, (
                ticket.get("id"),
                ticket.get("subject"),
                ticket.get("description"),
                json.dumps(comments) if comments else None,
                ticket.get("status"),
                ticket.get("created_at"),
                ticket.get("updated_at"),
                ticket.get("requester", {}).get("email") if isinstance(ticket.get("requester"), dict) else None,
                json.dumps(ticket.get("tags", [])),
                datetime.utcnow().isoformat(),
            ))

    def save_issue(self, ticket_id: int, issue: dict):
        """Save an extracted issue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO issues (ticket_id, category, issue_type, severity, summary, detail, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id,
                issue.get("category"),
                issue.get("issue_type"),
                issue.get("severity"),
                issue.get("summary"),
                issue.get("detail"),
                issue.get("confidence"),
            ))

    def get_unanalyzed_tickets(self) -> list[dict]:
        """Get tickets that haven't been analyzed yet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT t.* FROM tickets t
                LEFT JOIN issues i ON t.zendesk_id = i.ticket_id
                WHERE i.id IS NULL
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_tickets(self) -> list[dict]:
        """Get all tickets."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_issues(self) -> list[dict]:
        """Get all extracted issues."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT i.*, t.subject as ticket_subject, t.zendesk_id
                FROM issues i
                JOIN tickets t ON i.ticket_id = t.zendesk_id
                ORDER BY i.extracted_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_issue_summary(self) -> dict:
        """Get summary statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            total_tickets = conn.execute("SELECT COUNT(*) as c FROM tickets").fetchone()["c"]
            total_issues = conn.execute("SELECT COUNT(*) as c FROM issues").fetchone()["c"]

            by_category = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM issues GROUP BY category ORDER BY count DESC
            """).fetchall()

            by_severity = conn.execute("""
                SELECT severity, COUNT(*) as count
                FROM issues GROUP BY severity ORDER BY count DESC
            """).fetchall()

            by_type = conn.execute("""
                SELECT issue_type, COUNT(*) as count
                FROM issues GROUP BY issue_type ORDER BY count DESC
            """).fetchall()

            return {
                "total_tickets": total_tickets,
                "total_issues": total_issues,
                "by_category": [dict(r) for r in by_category],
                "by_severity": [dict(r) for r in by_severity],
                "by_type": [dict(r) for r in by_type],
            }

    def clear_issues(self):
        """Clear all issues (useful for re-analysis)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM issues")


if __name__ == "__main__":
    from rich import print as rprint

    storage = Storage()
    rprint("[green]Database initialized successfully[/green]")

    summary = storage.get_issue_summary()
    rprint(f"Tickets: {summary['total_tickets']}, Issues: {summary['total_issues']}")
