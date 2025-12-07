"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-12-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes for the Product Issue Miner application."""

    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('zendesk_ticket_id', sa.BigInteger(), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('public_comments', sa.Text(), nullable=True),
        sa.Column('requester_email', sa.String(length=255), nullable=True),
        sa.Column('requester_org_name', sa.String(length=255), nullable=True),
        sa.Column('zendesk_org_id', sa.BigInteger(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('ticket_created_at', sa.DateTime(), nullable=False),
        sa.Column('ticket_updated_at', sa.DateTime(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tickets_zendesk_ticket_id', 'tickets', ['zendesk_ticket_id'], unique=True)
    op.create_index('idx_tickets_updated', 'tickets', ['ticket_updated_at'], unique=False)
    op.create_index('idx_tickets_analyzed', 'tickets', ['analyzed_at'], unique=False)

    # Create issue_clusters table
    op.create_table(
        'issue_clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subcategory', sa.String(length=50), nullable=False),
        sa.Column('cluster_name', sa.String(length=200), nullable=False),
        sa.Column('cluster_summary', sa.Text(), nullable=True),
        sa.Column('issue_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unique_customers', sa.Integer(), server_default='0', nullable=False),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('count_7d', sa.Integer(), server_default='0', nullable=False),
        sa.Column('count_prior_7d', sa.Integer(), server_default='0', nullable=False),
        sa.Column('trend_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('pm_status', sa.String(length=50), server_default="'new'", nullable=False),
        sa.Column('pm_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "pm_status IN ('new', 'reviewing', 'acknowledged', 'fixed', 'wont_fix')",
            name='check_valid_pm_status'
        ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_clusters_category', 'issue_clusters', ['category', 'subcategory'], unique=False)
    op.create_index('idx_clusters_active', 'issue_clusters', ['is_active', sa.text('issue_count DESC')], unique=False)

    # Create extracted_issues table
    op.create_table(
        'extracted_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cluster_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subcategory', sa.String(length=50), nullable=False),
        sa.Column('issue_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('representative_quote', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "category IN ('TIME_AND_ATTENDANCE', 'PAYROLL', 'SETTINGS')",
            name='check_valid_category'
        ),
        sa.CheckConstraint(
            "issue_type IN ('bug', 'friction', 'ux_confusion', 'feature_request', 'documentation_gap', 'data_issue')",
            name='check_valid_issue_type'
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name='check_valid_severity'
        ),
        sa.CheckConstraint(
            'confidence >= 0.00 AND confidence <= 1.00',
            name='check_confidence_range'
        ),
        sa.ForeignKeyConstraint(['cluster_id'], ['issue_clusters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_issues_category', 'extracted_issues', ['category', 'subcategory'], unique=False)
    op.create_index('idx_issues_severity', 'extracted_issues', ['severity'], unique=False)
    op.create_index('idx_issues_cluster', 'extracted_issues', ['cluster_id'], unique=False)
    op.create_index('idx_issues_extracted', 'extracted_issues', ['extracted_at'], unique=False)

    # Create sync_state table
    op.create_table(
        'sync_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('last_ticket_updated_at', sa.DateTime(), nullable=False),
        sa.Column('tickets_synced', sa.Integer(), server_default='0', nullable=False),
        sa.Column('issues_extracted', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sync_completed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('sync_state')
    op.drop_table('extracted_issues')
    op.drop_table('issue_clusters')
    op.drop_table('tickets')
