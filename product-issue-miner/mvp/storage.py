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
                    problem_statement TEXT,
                    confidence REAL,
                    user_segment TEXT,
                    platform TEXT,
                    frequency TEXT,
                    has_workaround INTEGER,
                    root_cause_hint TEXT,
                    business_impact TEXT,
                    related_feature TEXT,
                    theme_id INTEGER,
                    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(zendesk_id),
                    FOREIGN KEY (theme_id) REFERENCES themes(id)
                );

                CREATE TABLE IF NOT EXISTS themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    product_area TEXT,
                    summary TEXT,
                    specific_feedback TEXT,
                    representative_quotes TEXT,
                    feature_workflow TEXT,
                    issue_count INTEGER DEFAULT 0,
                    unique_customers INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    trend_7d_pct REAL,
                    pm_status TEXT DEFAULT 'new',
                    pm_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tickets_zendesk_id ON tickets(zendesk_id);
                CREATE INDEX IF NOT EXISTS idx_issues_ticket_id ON issues(ticket_id);
                CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
                CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity);
                CREATE INDEX IF NOT EXISTS idx_issues_theme_id ON issues(theme_id);
                CREATE INDEX IF NOT EXISTS idx_themes_product_area ON themes(product_area);
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
                INSERT INTO issues (ticket_id, category, issue_type, severity, summary, detail, problem_statement,
                                    confidence, user_segment, platform, frequency, has_workaround, root_cause_hint,
                                    business_impact, related_feature, theme_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id,
                issue.get("category"),
                issue.get("issue_type"),
                issue.get("severity"),
                issue.get("summary"),
                issue.get("detail"),
                issue.get("problem_statement"),
                issue.get("confidence"),
                issue.get("user_segment"),
                issue.get("platform"),
                issue.get("frequency"),
                1 if issue.get("has_workaround") else (0 if issue.get("has_workaround") is False else None),
                issue.get("root_cause_hint"),
                issue.get("business_impact"),
                issue.get("related_feature"),
                issue.get("theme_id"),
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

    # --- Theme methods ---

    def save_theme(self, theme: dict) -> int:
        """Save a new theme and return its ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO themes (name, product_area, summary, specific_feedback, representative_quotes,
                                    feature_workflow, issue_count, unique_customers, first_seen, last_seen,
                                    trend_7d_pct, pm_status, pm_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                theme.get("name"),
                theme.get("product_area"),
                theme.get("summary"),
                json.dumps(theme.get("specific_feedback", [])),
                json.dumps(theme.get("representative_quotes", [])),
                theme.get("feature_workflow"),
                theme.get("issue_count", 0),
                theme.get("unique_customers", 0),
                theme.get("first_seen"),
                theme.get("last_seen"),
                theme.get("trend_7d_pct"),
                theme.get("pm_status", "new"),
                theme.get("pm_notes"),
            ))
            return cursor.lastrowid

    def update_theme(self, theme_id: int, theme: dict):
        """Update an existing theme."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE themes SET
                    name = ?, product_area = ?, summary = ?, specific_feedback = ?,
                    representative_quotes = ?, feature_workflow = ?, issue_count = ?,
                    unique_customers = ?, first_seen = ?, last_seen = ?, trend_7d_pct = ?,
                    pm_status = ?, pm_notes = ?, updated_at = ?
                WHERE id = ?
            """, (
                theme.get("name"),
                theme.get("product_area"),
                theme.get("summary"),
                json.dumps(theme.get("specific_feedback", [])),
                json.dumps(theme.get("representative_quotes", [])),
                theme.get("feature_workflow"),
                theme.get("issue_count", 0),
                theme.get("unique_customers", 0),
                theme.get("first_seen"),
                theme.get("last_seen"),
                theme.get("trend_7d_pct"),
                theme.get("pm_status", "new"),
                theme.get("pm_notes"),
                datetime.utcnow().isoformat(),
                theme_id,
            ))

    def assign_issue_to_theme(self, issue_id: int, theme_id: int):
        """Assign an issue to a theme."""
        with self._get_conn() as conn:
            conn.execute("UPDATE issues SET theme_id = ? WHERE id = ?", (theme_id, issue_id))

    def get_all_themes(self) -> list[dict]:
        """Get all themes ordered by issue count."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM themes ORDER BY issue_count DESC
            """)
            themes = []
            for row in cursor.fetchall():
                theme = dict(row)
                theme["specific_feedback"] = json.loads(theme["specific_feedback"]) if theme["specific_feedback"] else []
                theme["representative_quotes"] = json.loads(theme["representative_quotes"]) if theme["representative_quotes"] else []
                themes.append(theme)
            return themes

    def get_theme(self, theme_id: int) -> dict | None:
        """Get a single theme by ID."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("SELECT * FROM themes WHERE id = ?", (theme_id,))
            row = cursor.fetchone()
            if row:
                theme = dict(row)
                theme["specific_feedback"] = json.loads(theme["specific_feedback"]) if theme["specific_feedback"] else []
                theme["representative_quotes"] = json.loads(theme["representative_quotes"]) if theme["representative_quotes"] else []
                return theme
            return None

    def get_issues_by_theme(self, theme_id: int) -> list[dict]:
        """Get all issues belonging to a theme."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT i.*, t.subject as ticket_subject, t.zendesk_id, t.requester_email
                FROM issues i
                JOIN tickets t ON i.ticket_id = t.zendesk_id
                WHERE i.theme_id = ?
                ORDER BY i.extracted_at DESC
            """, (theme_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_unthemed_issues(self) -> list[dict]:
        """Get all issues not assigned to a theme."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT i.*, t.subject as ticket_subject, t.zendesk_id, t.requester_email
                FROM issues i
                JOIN tickets t ON i.ticket_id = t.zendesk_id
                WHERE i.theme_id IS NULL
                ORDER BY i.extracted_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_issues_for_theming(self) -> list[dict]:
        """Get all issues with fields needed for theme generation."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            cursor = conn.execute("""
                SELECT i.id, i.ticket_id, i.category, i.issue_type, i.severity, i.summary,
                       i.detail, i.problem_statement, i.related_feature, i.business_impact,
                       i.theme_id, t.requester_email, t.zendesk_id
                FROM issues i
                JOIN tickets t ON i.ticket_id = t.zendesk_id
                ORDER BY i.extracted_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def clear_themes(self):
        """Clear all themes and unassign issues."""
        with self._get_conn() as conn:
            conn.execute("UPDATE issues SET theme_id = NULL")
            conn.execute("DELETE FROM themes")

    def get_theme_summary(self) -> dict:
        """Get summary statistics for themes."""
        with self._get_conn() as conn:
            conn.row_factory = self._sqlite3.Row
            total_themes = conn.execute("SELECT COUNT(*) as c FROM themes").fetchone()["c"]
            themed_issues = conn.execute("SELECT COUNT(*) as c FROM issues WHERE theme_id IS NOT NULL").fetchone()["c"]
            unthemed_issues = conn.execute("SELECT COUNT(*) as c FROM issues WHERE theme_id IS NULL").fetchone()["c"]
            by_product_area = conn.execute("""
                SELECT product_area, COUNT(*) as theme_count, SUM(issue_count) as total_issues
                FROM themes
                GROUP BY product_area
                ORDER BY total_issues DESC
            """).fetchall()
            return {
                "total_themes": total_themes,
                "themed_issues": themed_issues,
                "unthemed_issues": unthemed_issues,
                "by_product_area": [dict(r) for r in by_product_area],
            }


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
                        problem_statement TEXT,
                        confidence REAL,
                        user_segment TEXT,
                        platform TEXT,
                        frequency TEXT,
                        has_workaround BOOLEAN,
                        root_cause_hint TEXT,
                        business_impact TEXT,
                        related_feature TEXT,
                        theme_id INTEGER,
                        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS themes (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        product_area TEXT,
                        summary TEXT,
                        specific_feedback TEXT,
                        representative_quotes TEXT,
                        feature_workflow TEXT,
                        issue_count INTEGER DEFAULT 0,
                        unique_customers INTEGER DEFAULT 0,
                        first_seen TIMESTAMP,
                        last_seen TIMESTAMP,
                        trend_7d_pct REAL,
                        pm_status TEXT DEFAULT 'new',
                        pm_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_tickets_zendesk_id ON tickets(zendesk_id);
                    CREATE INDEX IF NOT EXISTS idx_issues_ticket_id ON issues(ticket_id);
                    CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
                    CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(severity);
                    CREATE INDEX IF NOT EXISTS idx_issues_theme_id ON issues(theme_id);
                    CREATE INDEX IF NOT EXISTS idx_themes_product_area ON themes(product_area);
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
                    INSERT INTO issues (ticket_id, category, issue_type, severity, summary, detail, problem_statement,
                                        confidence, user_segment, platform, frequency, has_workaround, root_cause_hint,
                                        business_impact, related_feature, theme_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticket_id,
                    issue.get("category"),
                    issue.get("issue_type"),
                    issue.get("severity"),
                    issue.get("summary"),
                    issue.get("detail"),
                    issue.get("problem_statement"),
                    issue.get("confidence"),
                    issue.get("user_segment"),
                    issue.get("platform"),
                    issue.get("frequency"),
                    issue.get("has_workaround"),
                    issue.get("root_cause_hint"),
                    issue.get("business_impact"),
                    issue.get("related_feature"),
                    issue.get("theme_id"),
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

    # --- Theme methods ---

    def save_theme(self, theme: dict) -> int:
        """Save a new theme and return its ID."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO themes (name, product_area, summary, specific_feedback, representative_quotes,
                                        feature_workflow, issue_count, unique_customers, first_seen, last_seen,
                                        trend_7d_pct, pm_status, pm_notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    theme.get("name"),
                    theme.get("product_area"),
                    theme.get("summary"),
                    json.dumps(theme.get("specific_feedback", [])),
                    json.dumps(theme.get("representative_quotes", [])),
                    theme.get("feature_workflow"),
                    theme.get("issue_count", 0),
                    theme.get("unique_customers", 0),
                    theme.get("first_seen"),
                    theme.get("last_seen"),
                    theme.get("trend_7d_pct"),
                    theme.get("pm_status", "new"),
                    theme.get("pm_notes"),
                ))
                theme_id = cur.fetchone()[0]
            conn.commit()
            return theme_id

    def update_theme(self, theme_id: int, theme: dict):
        """Update an existing theme."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE themes SET
                        name = %s, product_area = %s, summary = %s, specific_feedback = %s,
                        representative_quotes = %s, feature_workflow = %s, issue_count = %s,
                        unique_customers = %s, first_seen = %s, last_seen = %s, trend_7d_pct = %s,
                        pm_status = %s, pm_notes = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    theme.get("name"),
                    theme.get("product_area"),
                    theme.get("summary"),
                    json.dumps(theme.get("specific_feedback", [])),
                    json.dumps(theme.get("representative_quotes", [])),
                    theme.get("feature_workflow"),
                    theme.get("issue_count", 0),
                    theme.get("unique_customers", 0),
                    theme.get("first_seen"),
                    theme.get("last_seen"),
                    theme.get("trend_7d_pct"),
                    theme.get("pm_status", "new"),
                    theme.get("pm_notes"),
                    datetime.utcnow(),
                    theme_id,
                ))
            conn.commit()

    def assign_issue_to_theme(self, issue_id: int, theme_id: int):
        """Assign an issue to a theme."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE issues SET theme_id = %s WHERE id = %s", (theme_id, issue_id))
            conn.commit()

    def get_all_themes(self) -> list[dict]:
        """Get all themes ordered by issue count."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM themes ORDER BY issue_count DESC")
                themes = []
                for row in cur.fetchall():
                    theme = dict(row)
                    theme["specific_feedback"] = json.loads(theme["specific_feedback"]) if theme["specific_feedback"] else []
                    theme["representative_quotes"] = json.loads(theme["representative_quotes"]) if theme["representative_quotes"] else []
                    themes.append(theme)
                return themes

    def get_theme(self, theme_id: int) -> dict | None:
        """Get a single theme by ID."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM themes WHERE id = %s", (theme_id,))
                row = cur.fetchone()
                if row:
                    theme = dict(row)
                    theme["specific_feedback"] = json.loads(theme["specific_feedback"]) if theme["specific_feedback"] else []
                    theme["representative_quotes"] = json.loads(theme["representative_quotes"]) if theme["representative_quotes"] else []
                    return theme
                return None

    def get_issues_by_theme(self, theme_id: int) -> list[dict]:
        """Get all issues belonging to a theme."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT i.*, t.subject as ticket_subject, t.zendesk_id, t.requester_email
                    FROM issues i
                    JOIN tickets t ON i.ticket_id = t.zendesk_id
                    WHERE i.theme_id = %s
                    ORDER BY i.extracted_at DESC
                """, (theme_id,))
                return [dict(row) for row in cur.fetchall()]

    def get_unthemed_issues(self) -> list[dict]:
        """Get all issues not assigned to a theme."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT i.*, t.subject as ticket_subject, t.zendesk_id, t.requester_email
                    FROM issues i
                    JOIN tickets t ON i.ticket_id = t.zendesk_id
                    WHERE i.theme_id IS NULL
                    ORDER BY i.extracted_at DESC
                """)
                return [dict(row) for row in cur.fetchall()]

    def get_issues_for_theming(self) -> list[dict]:
        """Get all issues with fields needed for theme generation."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT i.id, i.ticket_id, i.category, i.issue_type, i.severity, i.summary,
                           i.detail, i.problem_statement, i.related_feature, i.business_impact,
                           i.theme_id, t.requester_email, t.zendesk_id
                    FROM issues i
                    JOIN tickets t ON i.ticket_id = t.zendesk_id
                    ORDER BY i.extracted_at DESC
                """)
                return [dict(row) for row in cur.fetchall()]

    def clear_themes(self):
        """Clear all themes and unassign issues."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE issues SET theme_id = NULL")
                cur.execute("DELETE FROM themes")
            conn.commit()

    def get_theme_summary(self) -> dict:
        """Get summary statistics for themes."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) as c FROM themes")
                total_themes = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) as c FROM issues WHERE theme_id IS NOT NULL")
                themed_issues = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) as c FROM issues WHERE theme_id IS NULL")
                unthemed_issues = cur.fetchone()["c"]
                cur.execute("""
                    SELECT product_area, COUNT(*) as theme_count, SUM(issue_count) as total_issues
                    FROM themes
                    GROUP BY product_area
                    ORDER BY total_issues DESC
                """)
                by_product_area = [dict(r) for r in cur.fetchall()]
                return {
                    "total_themes": total_themes,
                    "themed_issues": themed_issues,
                    "unthemed_issues": unthemed_issues,
                    "by_product_area": by_product_area,
                }


# Backwards compatibility alias
Storage = SQLiteStorage


if __name__ == "__main__":
    from rich import print as rprint

    storage = get_storage()
    db_type = "PostgreSQL" if isinstance(storage, PostgresStorage) else "SQLite"
    rprint(f"[green]Using {db_type} database[/green]")

    summary = storage.get_issue_summary()
    rprint(f"Tickets: {summary['total_tickets']}, Issues: {summary['total_issues']}")
