# Database Schema

SQLAlchemy 2.0 models for the Product Issue Miner application.

## Models

### 1. Ticket (`app/models/ticket.py`)

Stores Zendesk support tickets synced from the Zendesk API.

**Table:** `tickets`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default: gen_random_uuid() | Primary key |
| zendesk_ticket_id | BigInteger | NOT NULL, UNIQUE, indexed | Zendesk ticket ID |
| subject | String(500) | nullable | Ticket subject |
| description | Text | nullable | Ticket description |
| internal_notes | Text | nullable | Internal agent notes |
| public_comments | Text | nullable | Public comments |
| requester_email | String(255) | nullable | Customer email |
| requester_org_name | String(255) | nullable | Customer organization |
| zendesk_org_id | BigInteger | nullable | Zendesk org ID |
| tags | JSONB | default: [] | Ticket tags |
| status | String(50) | nullable | Ticket status |
| priority | String(50) | nullable | Ticket priority |
| ticket_created_at | DateTime | NOT NULL | When ticket was created |
| ticket_updated_at | DateTime | NOT NULL, indexed | When ticket was last updated |
| synced_at | DateTime | default: now() | When synced to our DB |
| analyzed_at | DateTime | nullable, indexed | When analyzed for issues |

**Indexes:**
- `ix_tickets_zendesk_ticket_id` (unique)
- `idx_tickets_updated` on `ticket_updated_at`
- `idx_tickets_analyzed` on `analyzed_at`

**Relationships:**
- `issues`: One-to-many with ExtractedIssue (cascade delete)

---

### 2. ExtractedIssue (`app/models/issue.py`)

Product issues extracted from tickets using LLM analysis.

**Table:** `extracted_issues`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default: gen_random_uuid() | Primary key |
| ticket_id | UUID | FK to tickets.id, ON DELETE CASCADE | Parent ticket |
| cluster_id | UUID | FK to issue_clusters.id, ON DELETE SET NULL, indexed | Cluster assignment |
| category | String(50) | NOT NULL, indexed, CHECK constraint | Product category |
| subcategory | String(50) | NOT NULL, indexed | Product subcategory |
| issue_type | String(50) | NOT NULL, CHECK constraint | Type of issue |
| severity | String(20) | NOT NULL, indexed, CHECK constraint | Issue severity |
| summary | String(500) | NOT NULL | Brief summary |
| detail | Text | nullable | Detailed description |
| representative_quote | Text | nullable | Quote from ticket |
| confidence | Numeric(3,2) | nullable, CHECK 0.00-1.00 | Confidence score |
| extracted_at | DateTime | default: now(), indexed | When extracted |

**Check Constraints:**
- `check_valid_category`: category IN ('TIME_AND_ATTENDANCE', 'PAYROLL', 'SETTINGS')
- `check_valid_issue_type`: issue_type IN ('bug', 'friction', 'ux_confusion', 'feature_request', 'documentation_gap', 'data_issue')
- `check_valid_severity`: severity IN ('critical', 'high', 'medium', 'low')
- `check_confidence_range`: confidence >= 0.00 AND confidence <= 1.00

**Indexes:**
- `idx_issues_category` on `(category, subcategory)`
- `idx_issues_severity` on `severity`
- `idx_issues_cluster` on `cluster_id`
- `idx_issues_extracted` on `extracted_at`

**Relationships:**
- `ticket`: Many-to-one with Ticket
- `cluster`: Many-to-one with IssueCluster

---

### 3. IssueCluster (`app/models/cluster.py`)

Clusters of similar issues for trend analysis and PM tracking.

**Table:** `issue_clusters`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default: gen_random_uuid() | Primary key |
| category | String(50) | NOT NULL, indexed | Product category |
| subcategory | String(50) | NOT NULL, indexed | Product subcategory |
| cluster_name | String(200) | NOT NULL | Cluster name |
| cluster_summary | Text | nullable | Summary description |
| issue_count | Integer | default: 0 | Total issues in cluster |
| unique_customers | Integer | default: 0 | Unique customer count |
| first_seen | DateTime | nullable | First occurrence |
| last_seen | DateTime | nullable | Last occurrence |
| count_7d | Integer | default: 0 | Count last 7 days |
| count_prior_7d | Integer | default: 0 | Count prior 7 days |
| trend_pct | Numeric(5,2) | nullable | Trend percentage |
| is_active | Boolean | default: true, indexed | Active flag |
| pm_status | String(50) | default: 'new', CHECK constraint | PM tracking status |
| pm_notes | Text | nullable | PM notes |
| created_at | DateTime | default: now() | Created timestamp |
| updated_at | DateTime | default: now() | Updated timestamp |

**Check Constraints:**
- `check_valid_pm_status`: pm_status IN ('new', 'reviewing', 'acknowledged', 'fixed', 'wont_fix')

**Indexes:**
- `idx_clusters_category` on `(category, subcategory)`
- `idx_clusters_active` on `(is_active, issue_count DESC)`

**Relationships:**
- `issues`: One-to-many with ExtractedIssue

---

### 4. SyncState (`app/models/sync_state.py`)

Tracks Zendesk sync progress (singleton table).

**Table:** `sync_state`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Serial | PK, autoincrement | Primary key |
| last_ticket_updated_at | DateTime | NOT NULL | Last processed ticket timestamp |
| tickets_synced | Integer | default: 0 | Total tickets synced |
| issues_extracted | Integer | default: 0 | Total issues extracted |
| sync_completed_at | DateTime | default: now() | Sync completion time |

---

## Product Taxonomy Constants

Defined in `app/models/__init__.py`:

### Categories
```python
CATEGORIES = ["TIME_AND_ATTENDANCE", "PAYROLL", "SETTINGS"]
```

### Subcategories
```python
SUBCATEGORIES = {
    "TIME_AND_ATTENDANCE": [
        "hardware_issues",
        "punch_in_out",
        "biometric_registration",
        "pto",
        "reporting",
        "corrections",
    ],
    "PAYROLL": [
        "pay_runs",
        "tax_questions",
        "direct_deposits",
        "reporting",
        "errors",
    ],
    "SETTINGS": [
        "employee_registration",
        "biometric_enrollment",
        "deductions",
    ],
}
```

### Issue Types
```python
ISSUE_TYPES = [
    "bug",
    "friction",
    "ux_confusion",
    "feature_request",
    "documentation_gap",
    "data_issue",
]
```

### Severities
```python
SEVERITIES = ["critical", "high", "medium", "low"]
```

### PM Statuses
```python
PM_STATUSES = ["new", "reviewing", "acknowledged", "fixed", "wont_fix"]
```

---

## Entity Relationships

```
tickets
  |
  +-- (1:N) --> extracted_issues
                      |
                      +-- (N:1) --> issue_clusters
```

- One ticket can have multiple extracted issues (cascade delete)
- Multiple issues can belong to one cluster (set null on cluster delete)

---

## Migration

Initial migration created: `alembic/versions/001_initial_schema.py`

### Run Migration

```bash
# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## SQLAlchemy 2.0 Features

All models use modern SQLAlchemy 2.0 patterns:

- **Mapped types**: `Mapped[Type]` for all columns
- **mapped_column()**: Type-safe column definitions
- **Relationship annotations**: Type hints for relationships
- **UUID generation**: PostgreSQL `gen_random_uuid()` for UUIDs
- **Server defaults**: Database-level defaults for timestamps and defaults
- **Check constraints**: Database-level validation
- **Cascade operations**: Proper foreign key cascade behavior
- **Async support**: Compatible with async SQLAlchemy operations

---

## Files Created

1. `app/models/ticket.py` - Ticket model
2. `app/models/issue.py` - ExtractedIssue model
3. `app/models/cluster.py` - IssueCluster model
4. `app/models/sync_state.py` - SyncState model
5. `app/models/__init__.py` - Model exports and taxonomy constants
6. `alembic/versions/001_initial_schema.py` - Initial migration
7. `alembic/env.py` - Updated with model imports
