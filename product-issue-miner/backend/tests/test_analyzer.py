"""
Tests for Claude AI-powered issue analyzer.

Tests cover:
- Issue extraction from tickets
- Response parsing and validation
- Taxonomy validation
- Cluster naming
- Error handling for malformed responses
- Confidence scoring
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from decimal import Decimal

from app.services.analyzer import IssueAnalyzer
from app.services.prompts import CATEGORIES, ISSUE_TYPES, SEVERITIES


@pytest.mark.asyncio
@pytest.mark.analyzer
class TestIssueAnalyzer:
    """Test suite for IssueAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization with API key."""
        analyzer = IssueAnalyzer(api_key="test_api_key_12345")

        assert analyzer.client is not None
        assert analyzer.MODEL == "claude-sonnet-4-5-20250514"
        assert analyzer.MAX_TOKENS_EXTRACTION == 1024

    def test_extract_issues_success(self, sample_zendesk_ticket):
        """Test successful issue extraction."""
        analyzer = IssueAnalyzer(api_key="test_key")

        # Mock Claude API response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "Geofencing blocking valid clock-ins",
                                "detail": "Employees within geofence unable to clock in",
                                "representative_quote": "I can't clock in from parking lot",
                                "confidence": 0.90,
                            }
                        ],
                        "no_product_issue": False,
                        "skip_reason": None,
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert len(result["issues"]) == 1
            assert result["no_product_issue"] is False
            assert result["issues"][0]["category"] == "TIME_AND_ATTENDANCE"
            assert result["issues"][0]["severity"] == "high"
            mock_create.assert_called_once()

    def test_extract_issues_no_product_issue(self, sample_zendesk_ticket):
        """Test extraction when no product issue found."""
        analyzer = IssueAnalyzer(api_key="test_key")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [],
                        "no_product_issue": True,
                        "skip_reason": "Customer question about billing, not a product issue",
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert len(result["issues"]) == 0
            assert result["no_product_issue"] is True
            assert "billing" in result["skip_reason"]

    def test_extract_issues_multiple(self, sample_zendesk_ticket):
        """Test extracting multiple issues from one ticket."""
        analyzer = IssueAnalyzer(api_key="test_key")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "Clock-in failure",
                                "detail": "Cannot clock in",
                                "representative_quote": "Clock in broken",
                                "confidence": 0.85,
                            },
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Timesheet",
                                "issue_type": "ux_confusion",
                                "severity": "low",
                                "summary": "Confusing timesheet UI",
                                "detail": "Users confused by timesheet layout",
                                "representative_quote": "Can't find my hours",
                                "confidence": 0.60,
                            },
                        ],
                        "no_product_issue": False,
                        "skip_reason": None,
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert len(result["issues"]) == 2
            assert result["issues"][0]["severity"] == "high"
            assert result["issues"][1]["issue_type"] == "ux_confusion"

    def test_extract_issues_invalid_json(self, sample_zendesk_ticket):
        """Test handling of malformed JSON response."""
        analyzer = IssueAnalyzer(api_key="test_key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Invalid JSON {{{")]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            # Should return safe fallback
            assert len(result["issues"]) == 0
            assert result["no_product_issue"] is True
            assert "parse error" in result["skip_reason"].lower()

    def test_validate_issue_valid(self):
        """Test validation of valid issue."""
        analyzer = IssueAnalyzer(api_key="test_key")

        valid_issue = {
            "category": "TIME_AND_ATTENDANCE",
            "subcategory": "Clock In/Out",
            "issue_type": "bug",
            "severity": "high",
            "summary": "Test issue",
        }

        assert analyzer._validate_issue(valid_issue) is True

    def test_validate_issue_invalid_category(self):
        """Test validation rejects invalid category."""
        analyzer = IssueAnalyzer(api_key="test_key")

        invalid_issue = {
            "category": "INVALID_CATEGORY",
            "subcategory": "Something",
            "issue_type": "bug",
            "severity": "high",
            "summary": "Test",
        }

        assert analyzer._validate_issue(invalid_issue) is False

    def test_validate_issue_invalid_subcategory(self):
        """Test validation rejects invalid subcategory for category."""
        analyzer = IssueAnalyzer(api_key="test_key")

        invalid_issue = {
            "category": "TIME_AND_ATTENDANCE",
            "subcategory": "Invalid Subcategory",
            "issue_type": "bug",
            "severity": "high",
            "summary": "Test",
        }

        assert analyzer._validate_issue(invalid_issue) is False

    def test_validate_issue_invalid_issue_type(self):
        """Test validation rejects invalid issue type."""
        analyzer = IssueAnalyzer(api_key="test_key")

        invalid_issue = {
            "category": "PAYROLL",
            "subcategory": "Tax Calculations",
            "issue_type": "invalid_type",
            "severity": "high",
            "summary": "Test",
        }

        assert analyzer._validate_issue(invalid_issue) is False

    def test_validate_issue_invalid_severity(self):
        """Test validation rejects invalid severity."""
        analyzer = IssueAnalyzer(api_key="test_key")

        invalid_issue = {
            "category": "SETTINGS",
            "subcategory": "User Management",
            "issue_type": "bug",
            "severity": "super_critical",
            "summary": "Test",
        }

        assert analyzer._validate_issue(invalid_issue) is False

    def test_validate_issue_missing_summary(self):
        """Test validation rejects issue without summary."""
        analyzer = IssueAnalyzer(api_key="test_key")

        invalid_issue = {
            "category": "TIME_AND_ATTENDANCE",
            "subcategory": "Clock In/Out",
            "issue_type": "bug",
            "severity": "high",
            "summary": "",
        }

        assert analyzer._validate_issue(invalid_issue) is False

    def test_extract_issues_filters_invalid(self, sample_zendesk_ticket):
        """Test that invalid issues are filtered out."""
        analyzer = IssueAnalyzer(api_key="test_key")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "Valid issue",
                                "confidence": 0.85,
                            },
                            {
                                "category": "INVALID_CATEGORY",
                                "subcategory": "Something",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "Invalid issue",
                                "confidence": 0.85,
                            },
                        ],
                        "no_product_issue": False,
                        "skip_reason": None,
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            # Only valid issue should remain
            assert len(result["issues"]) == 1
            assert result["issues"][0]["summary"] == "Valid issue"

    def test_name_cluster_success(self):
        """Test successful cluster naming."""
        analyzer = IssueAnalyzer(api_key="test_key")

        issues = [
            {
                "category": "TIME_AND_ATTENDANCE",
                "subcategory": "Clock In/Out",
                "summary": "Geofencing prevents clock-in",
                "representative_quote": "Can't clock in from parking lot",
            },
            {
                "category": "TIME_AND_ATTENDANCE",
                "subcategory": "Clock In/Out",
                "summary": "Location validation failing",
                "representative_quote": "System says I'm too far away",
            },
        ]

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "cluster_name": "Geofencing Clock-In Failures",
                        "cluster_summary": "Multiple employees unable to clock in due to overly strict geofence validation",
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.name_cluster(issues)

            assert result["cluster_name"] == "Geofencing Clock-In Failures"
            assert "geofence" in result["cluster_summary"].lower()
            mock_create.assert_called_once()

    def test_name_cluster_malformed_response(self):
        """Test cluster naming with malformed JSON response."""
        analyzer = IssueAnalyzer(api_key="test_key")

        issues = [
            {
                "category": "PAYROLL",
                "subcategory": "Direct Deposit",
                "summary": "Direct deposit failing",
                "representative_quote": "Money didn't arrive",
            }
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Invalid JSON")]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.name_cluster(issues)

            # Should return fallback name
            assert "cluster_name" in result
            assert "PAYROLL" in result["cluster_name"]
            assert "Auto-generated" in result["cluster_summary"]

    def test_name_cluster_empty_issues(self):
        """Test cluster naming with empty issues list."""
        analyzer = IssueAnalyzer(api_key="test_key")

        with pytest.raises(Exception):
            analyzer.name_cluster([])

    def test_extract_issues_with_all_severities(self, sample_zendesk_ticket):
        """Test extraction covers all severity levels."""
        analyzer = IssueAnalyzer(api_key="test_key")

        issues_data = []
        for severity in SEVERITIES:
            issues_data.append(
                {
                    "category": "TIME_AND_ATTENDANCE",
                    "subcategory": "Clock In/Out",
                    "issue_type": "bug",
                    "severity": severity,
                    "summary": f"Issue with {severity} severity",
                    "confidence": 0.75,
                }
            )

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {"issues": issues_data, "no_product_issue": False, "skip_reason": None}
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert len(result["issues"]) == len(SEVERITIES)
            severities_found = {issue["severity"] for issue in result["issues"]}
            assert severities_found == set(SEVERITIES)

    def test_extract_issues_with_all_issue_types(self, sample_zendesk_ticket):
        """Test extraction covers all issue types."""
        analyzer = IssueAnalyzer(api_key="test_key")

        issues_data = []
        for issue_type in ISSUE_TYPES:
            issues_data.append(
                {
                    "category": "TIME_AND_ATTENDANCE",
                    "subcategory": "Clock In/Out",
                    "issue_type": issue_type,
                    "severity": "medium",
                    "summary": f"Issue of type {issue_type}",
                    "confidence": 0.75,
                }
            )

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {"issues": issues_data, "no_product_issue": False, "skip_reason": None}
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert len(result["issues"]) == len(ISSUE_TYPES)
            types_found = {issue["issue_type"] for issue in result["issues"]}
            assert types_found == set(ISSUE_TYPES)

    def test_extract_issues_confidence_values(self, sample_zendesk_ticket):
        """Test that confidence values are preserved."""
        analyzer = IssueAnalyzer(api_key="test_key")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "High confidence issue",
                                "confidence": 0.95,
                            },
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "low",
                                "summary": "Low confidence issue",
                                "confidence": 0.45,
                            },
                        ],
                        "no_product_issue": False,
                        "skip_reason": None,
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(sample_zendesk_ticket)

            assert result["issues"][0]["confidence"] == 0.95
            assert result["issues"][1]["confidence"] == 0.45


@pytest.mark.asyncio
@pytest.mark.analyzer
class TestAnalyzerIntegration:
    """Integration tests for analyzer with realistic scenarios."""

    def test_complete_ticket_analysis_flow(self):
        """Test complete flow from ticket to extracted issues."""
        analyzer = IssueAnalyzer(api_key="test_key")

        ticket = {
            "zendesk_ticket_id": 12345,
            "subject": "Can't clock in - geofencing issue",
            "description": "Employee reports being unable to clock in from work parking lot",
            "public_comments": "I'm in the parking lot but app says I'm too far away",
            "internal_notes": "Looks like geofence radius is too small",
            "requester_email": "employee@company.com",
            "requester_org_name": "Test Corp",
            "tags": ["product_issue", "time_attendance"],
            "ticket_created_at": "2024-01-15T10:00:00Z",
        }

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "issues": [
                            {
                                "category": "TIME_AND_ATTENDANCE",
                                "subcategory": "Clock In/Out",
                                "issue_type": "bug",
                                "severity": "high",
                                "summary": "Geofencing blocking valid clock-in attempts",
                                "detail": "Employees within valid work location unable to clock in due to geofence validation",
                                "representative_quote": "I'm in the parking lot but app says I'm too far away",
                                "confidence": 0.90,
                            }
                        ],
                        "no_product_issue": False,
                        "skip_reason": None,
                    }
                )
            )
        ]

        with patch.object(analyzer.client.messages, "create") as mock_create:
            mock_create.return_value = mock_response

            result = analyzer.extract_issues(ticket)

            assert len(result["issues"]) == 1
            issue = result["issues"][0]
            assert issue["category"] == "TIME_AND_ATTENDANCE"
            assert issue["subcategory"] == "Clock In/Out"
            assert "geofenc" in issue["summary"].lower()
            assert issue["confidence"] == 0.90
