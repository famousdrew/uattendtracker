"""
Database models for the Product Issue Miner application.

This module exports all SQLAlchemy models and taxonomy constants
used throughout the application.
"""

from app.models.ticket import Ticket
from app.models.issue import ExtractedIssue, VALID_CATEGORIES, VALID_ISSUE_TYPES, VALID_SEVERITIES
from app.models.cluster import IssueCluster, VALID_PM_STATUSES
from app.models.sync_state import SyncState

# Product taxonomy constants
CATEGORIES = ["TIME_AND_ATTENDANCE", "PAYROLL", "SETTINGS"]

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

ISSUE_TYPES = [
    "bug",
    "friction",
    "ux_confusion",
    "feature_request",
    "documentation_gap",
    "data_issue",
]

SEVERITIES = ["critical", "high", "medium", "low"]

PM_STATUSES = ["new", "reviewing", "acknowledged", "fixed", "wont_fix"]

# Export all models
__all__ = [
    "Ticket",
    "ExtractedIssue",
    "IssueCluster",
    "SyncState",
    "CATEGORIES",
    "SUBCATEGORIES",
    "ISSUE_TYPES",
    "SEVERITIES",
    "PM_STATUSES",
    "VALID_CATEGORIES",
    "VALID_ISSUE_TYPES",
    "VALID_SEVERITIES",
    "VALID_PM_STATUSES",
]
