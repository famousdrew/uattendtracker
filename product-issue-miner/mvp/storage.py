"""Storage layer - supports SQLite (local) and PostgreSQL (production)."""
import os
import json
from datetime import datetime
from urllib.parse import urlparse


def get_storage():
    """Factory function - returns PostgreSQL or SQLite storage based on DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres"):
        return PostgresStorage(database_url)
    return SQLiteStorage()


class SQLiteStorage:
    """SQLite-based storage for local development."""

    def __init__(self, db_path: str = "mvp_data.db"):
        import sqlite3
        self.db_path = db_path
        self._sqlite3 = sqlite3
        self._init_db()

    def _get_conn(self):
        return self._sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
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
        with self._get_conn() as conn:
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
        with self._get_conn() as conn:
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
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT t.* FROM tickets t
                LEFT JOIN issues i ON t.zendesk_id = i.ticket_id
                WHERE i.id IS NULL
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_tickets(self) -> list[dict]:
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_issues(self) -> list[dict]:
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT i.*, t.subject as ticket_subject, t.zendesk_id
                FROM issues i
                JOIN tickets t ON i.ticket_id = t.zendesk_id
                ORDER BY i.extracted_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_issue_summary(self) -> dict:
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            total_tickets = conn.execute("SELECT COUNT(*) as c FROM tickets").fetchone()["c"]
            total_issues = conn.execute("SELECT COUNT(*) as c FROM issues").fetchone()["c"]
            by_category = conn.execute("SELECT category, COUNT(*) as count FROM issues GROUP BY category ORDER BY count DESC").fetchall()
            by_severity = conn.execute("SELECT severity, COUNT(*) as count FROM issues GROUP BY severity ORDER BY count DESC").fetchall()
            by_type = conn.execute("SELECT issue_type, COUNT(*) as count FROM issues GROUP BY issue_type ORDER BY count DESC").fetchall()
            return {
                "total_tickets": total_tickets,
                "total_issues": total_issues,
                "by_category": [dict(r) for r in by_category],
                "by_severity": [dict(r) for r in by_severity],
                "by_type": [dict(r) for r in by_type],
            }

    def clear_issues(self):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM issues")

    def clear_all(self):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM issues")
            conn.execute("DELETE FROM tickets")


class PostgresStorage:
    """PostgreSQL storage for production."""

    def __init__(self, database_url: str):
        import psycopg2
        import psycopg2.extras
        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self.database_url = database_url
        self._init_db()

    def _get_conn(self):
        return self._psycopg2.connect(self.database_url)

    def _init_db(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id SERIAL PRIMARY KEY,
                        zendesk_id BIGINT UNIQUE NOT NULL,
                        subject TEXT,
                        description TEXT,
                        comments_json TEXT,
                        status TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        requester_email TEXT,
                        tags TEXT,
                        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS issues (
                        id SERIAL PRIMARY KEY,
                        ticket_id BIGINT NOT NULL REFERENCES tickets(zendesk_id),
                        category TEXT,
                        issue_type TEXT,
                        severity TEXT,
                        summary TEXT,
                        detail TEXT,
                        confidence REAL,
                        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_tickets_zendesk_id ON tickets(zendesk_id);
                    CREATE INDEX IF NOT EXISTS idx_issues_ticket_id ON issues(ticket_id);
                    CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
                    CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity);
                """)
            conn.commit()

    def upsert_ticket(self, ticket: dict, comments: list[dict] = None):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tickets (zendesk_id, subject, description, comments_json, status,
                                         created_at, updated_at, requester_email, tags, synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(zendesk_id) DO UPDATE SET
                        subject = EXCLUDED.subject,
                        description = EXCLUDED.description,
                        comments_json = EXCLUDED.comments_json,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at,
                        requester_email = EXCLUDED.requester_email,
                        tags = EXCLUDED.tags,
                        synced_at = EXCLUDED.synced_at
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
                    datetime.utcnow(),
                ))
            conn.commit()

    def save_issue(self, ticket_id: int, issue: dict):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO issues (ticket_id, category, issue_type, severity, summary, detail, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticket_id,
                    issue.get("category"),
                    issue.get("issue_type"),
                    issue.get("severity"),
                    issue.get("summary"),
                    issue.get("detail"),
                    issue.get("confidence"),
                ))
            conn.commit()

    def get_unanalyzed_tickets(self) -> list[dict]:
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT t.* FROM tickets t
                    LEFT JOIN issues i ON t.zendesk_id = i.ticket_id
                    WHERE i.id IS NULL
                """)
                return [dict(row) for row in cur.fetchall()]

    def get_all_tickets(self) -> list[dict]:
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM tickets ORDER BY created_at DESC")
                return [dict(row) for row in cur.fetchall()]

    def get_all_issues(self) -> list[dict]:
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT i.*, t.subject as ticket_subject, t.zendesk_id
                    FROM issues i
                    JOIN tickets t ON i.ticket_id = t.zendesk_id
                    ORDER BY i.extracted_at DESC
                """)
                return [dict(row) for row in cur.fetchall()]

    def get_issue_summary(self) -> dict:
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) as c FROM tickets")
                total_tickets = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) as c FROM issues")
                total_issues = cur.fetchone()["c"]
                cur.execute("SELECT category, COUNT(*) as count FROM issues GROUP BY category ORDER BY count DESC")
                by_category = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT severity, COUNT(*) as count FROM issues GROUP BY severity ORDER BY count DESC")
                by_severity = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT issue_type, COUNT(*) as count FROM issues GROUP BY issue_type ORDER BY count DESC")
                by_type = [dict(r) for r in cur.fetchall()]
                return {
                    "total_tickets": total_tickets,
                    "total_issues": total_issues,
                    "by_category": by_category,
                    "by_severity": by_severity,
                    "by_type": by_type,
                }

    def clear_issues(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM issues")
            conn.commit()

    def clear_all(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM issues")
                cur.execute("DELETE FROM tickets")
            conn.commit()


# Backwards compatibility alias
Storage = SQLiteStorage


if __name__ == "__main__":
    from rich import print as rprint

    storage = get_storage()
    db_type = "PostgreSQL" if isinstance(storage, PostgresStorage) else "SQLite"
    rprint(f"[green]Using {db_type} database[/green]")

    summary = storage.get_issue_summary()
    rprint(f"Tickets: {summary['total_tickets']}, Issues: {summary['total_issues']}")
