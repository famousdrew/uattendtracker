"""
Claude AI-powered issue analyzer for ticket processing.

This module provides the IssueAnalyzer class that uses Claude AI to:
1. Extract product issues from support tickets
2. Generate names and summaries for issue clusters
"""

import json
import logging
from typing import Optional
import anthropic

from app.services.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    CLUSTER_NAMING_PROMPT,
    build_extraction_user_prompt,
    build_cluster_naming_prompt,
    CATEGORIES,
    ISSUE_TYPES,
    SEVERITIES
)

logger = logging.getLogger(__name__)


class IssueAnalyzer:
    """
    Analyzes tickets using Claude to extract product issues.

    Uses Claude Sonnet 4.5 to:
    - Extract structured product issues from unstructured ticket data
    - Validate extracted issues against product taxonomy
    - Generate cluster names and summaries for grouped issues
    """

    MODEL = "claude-sonnet-4-5-20250514"
    MAX_TOKENS_EXTRACTION = 1024
    MAX_TOKENS_NAMING = 256

    def __init__(self, api_key: str):
        """
        Initialize the analyzer with Anthropic API credentials.

        Args:
            api_key: Anthropic API key for Claude access
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def extract_issues(self, ticket: dict) -> dict:
        """
        Extract product issues from a ticket using Claude.

        Args:
            ticket: Dictionary with keys:
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
            Dictionary with structure:
            {
                "issues": [
                    {
                        "category": str,
                        "subcategory": str,
                        "issue_type": str,
                        "severity": str,
                        "summary": str,
                        "detail": str,
                        "representative_quote": str,
                        "confidence": float
                    }
                ],
                "no_product_issue": bool,
                "skip_reason": Optional[str]
            }

        Raises:
            anthropic.APIError: If the Claude API call fails
        """
        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS_EXTRACTION,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": build_extraction_user_prompt(ticket)}
                ]
            )

            result = json.loads(response.content[0].text)

            # Validate extracted issues
            validated_issues = []
            for issue in result.get('issues', []):
                if self._validate_issue(issue):
                    validated_issues.append(issue)
                else:
                    logger.warning(
                        f"Invalid issue extracted from ticket {ticket.get('zendesk_ticket_id')}: {issue}"
                    )

            result['issues'] = validated_issues
            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse Claude response for ticket {ticket.get('zendesk_ticket_id')}: {e}"
            )
            return {
                "issues": [],
                "no_product_issue": True,
                "skip_reason": "AI response parse error"
            }
        except anthropic.APIError as e:
            logger.error(
                f"Claude API error for ticket {ticket.get('zendesk_ticket_id')}: {e}"
            )
            raise

    def name_cluster(self, issues: list) -> dict:
        """
        Generate a name and summary for a cluster of issues.

        Args:
            issues: List of issue dictionaries with keys:
                   - category: Issue category
                   - subcategory: Issue subcategory
                   - summary: Issue summary
                   - representative_quote: Quote from ticket

        Returns:
            Dictionary with structure:
            {
                "cluster_name": str,
                "cluster_summary": str
            }

        Raises:
            anthropic.APIError: If the Claude API call fails
        """
        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS_NAMING,
                system=CLUSTER_NAMING_PROMPT,
                messages=[
                    {"role": "user", "content": build_cluster_naming_prompt(issues)}
                ]
            )

            return json.loads(response.content[0].text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cluster naming response: {e}")
            # Fallback to auto-generated name
            return {
                "cluster_name": f"{issues[0].get('category', 'Unknown')}: {issues[0].get('summary', 'Unknown')[:50]}",
                "cluster_summary": "Auto-generated cluster name due to AI response error"
            }
        except anthropic.APIError as e:
            logger.error(f"Claude API error for cluster naming: {e}")
            raise

    def _validate_issue(self, issue: dict) -> bool:
        """
        Validate that an extracted issue has valid taxonomy values.

        Args:
            issue: Issue dictionary to validate

        Returns:
            True if issue is valid, False otherwise
        """
        category = issue.get('category')
        subcategory = issue.get('subcategory')
        issue_type = issue.get('issue_type')
        severity = issue.get('severity')

        if category not in CATEGORIES:
            logger.warning(f"Invalid category: {category}")
            return False
        if subcategory not in CATEGORIES.get(category, []):
            logger.warning(f"Invalid subcategory: {subcategory} for category: {category}")
            return False
        if issue_type not in ISSUE_TYPES:
            logger.warning(f"Invalid issue_type: {issue_type}")
            return False
        if severity not in SEVERITIES:
            logger.warning(f"Invalid severity: {severity}")
            return False
        if not issue.get('summary'):
            logger.warning("Missing summary")
            return False

        return True


def get_analyzer() -> IssueAnalyzer:
    """
    Factory function to create an IssueAnalyzer instance with config from settings.

    Returns:
        Configured IssueAnalyzer instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not configured in settings
    """
    from app.config import settings

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY must be configured in environment or .env file")

    return IssueAnalyzer(api_key=settings.ANTHROPIC_API_KEY)
