"""
Prompt templates and taxonomy for Claude AI issue extraction.

This module contains:
- Product taxonomy (categories, subcategories, issue types, severities)
- System prompts for issue extraction and cluster naming
- Prompt builder functions
"""

# Product Taxonomy
CATEGORIES = {
    "TIME_AND_ATTENDANCE": [
        "hardware_issues",
        "punch_in_out",
        "biometric_registration",
        "pto",
        "reporting",
        "corrections"
    ],
    "PAYROLL": [
        "pay_runs",
        "tax_questions",
        "direct_deposits",
        "reporting",
        "errors"
    ],
    "SETTINGS": [
        "employee_registration",
        "biometric_enrollment",
        "deductions"
    ]
}

ISSUE_TYPES = ["bug", "friction", "ux_confusion", "feature_request", "documentation_gap", "data_issue"]
SEVERITIES = ["critical", "high", "medium", "low"]

EXTRACTION_SYSTEM_PROMPT = """You are a product analyst for a time & attendance + payroll SaaS company.
Analyze support tickets to extract product issues for the PM team.

PRODUCT TAXONOMY:
Categories: TIME_AND_ATTENDANCE, PAYROLL, SETTINGS

Subcategories:
- TIME_AND_ATTENDANCE: hardware_issues, punch_in_out, biometric_registration, pto, reporting, corrections
- PAYROLL: pay_runs, tax_questions, direct_deposits, reporting, errors
- SETTINGS: employee_registration, biometric_enrollment, deductions

Issue types: bug, friction, ux_confusion, feature_request, documentation_gap, data_issue

Severity:
- critical: Money/compliance issues, complete blockers
- high: Major workflow blocked, workaround painful
- medium: Impaired but functional
- low: Minor inconvenience

INSTRUCTIONS:
1. Read the ticket (subject, description, all comments including internal notes)
2. Identify DISTINCT product issues (0 if none, multiple if several issues)
3. Ignore pure support process issues (refund requests, account access, billing)
4. Use representative quotes that capture user pain

Respond with JSON only:
{
  "issues": [
    {
      "category": "TIME_AND_ATTENDANCE",
      "subcategory": "punch_in_out",
      "issue_type": "bug",
      "severity": "high",
      "summary": "Clock-in button unresponsive on Android app after OS update",
      "detail": "Multiple users reporting the clock-in button requires 3-4 taps after updating to Android 14.",
      "representative_quote": "My employees have to tap the button multiple times",
      "confidence": 0.92
    }
  ],
  "no_product_issue": false,
  "skip_reason": null
}

If no product issues:
{
  "issues": [],
  "no_product_issue": true,
  "skip_reason": "Billing inquiry only"
}"""

CLUSTER_NAMING_PROMPT = """Given a group of related product issues, generate a specific cluster name and summary.

Good names are specific and actionable:
✓ "Android 14 clock-in button tap delay"
✓ "CA state tax withholding errors"

Bad names are vague:
✗ "Mobile app issues"
✗ "Tax problems"

Respond with JSON:
{
  "cluster_name": "Specific name (max 100 chars)",
  "cluster_summary": "2-3 sentence summary of the issue pattern and business impact"
}"""


def build_extraction_user_prompt(ticket: dict) -> str:
    """
    Build the user prompt for issue extraction from a ticket.

    Args:
        ticket: Dictionary containing ticket data with keys:
               - zendesk_ticket_id: Ticket ID
               - subject: Ticket subject
               - description: Ticket description
               - public_comments: Public comments text
               - internal_notes: Internal notes text
               - requester_email: Email of requester
               - requester_org_name: Organization name
               - tags: List of tags
               - ticket_created_at: Creation timestamp

    Returns:
        Formatted prompt string for Claude
    """
    tags = ', '.join(ticket.get('tags', [])) if ticket.get('tags') else 'None'

    return f"""Analyze this ticket:

TICKET ID: {ticket.get('zendesk_ticket_id', 'Unknown')}
SUBJECT: {ticket.get('subject', 'No subject')}
CREATED: {ticket.get('ticket_created_at', 'Unknown')}
REQUESTER: {ticket.get('requester_email', 'Unknown')} ({ticket.get('requester_org_name') or 'No org'})
TAGS: {tags}

DESCRIPTION:
{ticket.get('description') or 'No description'}

PUBLIC COMMENTS:
{ticket.get('public_comments') or 'None'}

INTERNAL NOTES:
{ticket.get('internal_notes') or 'None'}"""


def build_cluster_naming_prompt(issues: list) -> str:
    """
    Build prompt for naming a cluster of issues.

    Args:
        issues: List of issue dictionaries containing:
               - category: Issue category
               - subcategory: Issue subcategory
               - summary: Issue summary
               - representative_quote: Quote from ticket

    Returns:
        Formatted prompt string for Claude
    """
    summaries = "\n".join([f"- {i.get('summary', '')}" for i in issues[:20]])
    quotes = "\n".join([f'- "{i.get("representative_quote", "")}"' for i in issues[:10] if i.get('representative_quote')])

    return f"""Category: {issues[0].get('category', 'Unknown')}
Subcategory: {issues[0].get('subcategory', 'Unknown')}
Number of tickets: {len(issues)}

Issue summaries:
{summaries}

Representative quotes:
{quotes}"""
