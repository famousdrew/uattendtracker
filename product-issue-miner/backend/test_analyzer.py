"""
Test script for IssueAnalyzer and prompts.

This script validates:
1. Taxonomy definitions
2. Prompt generation
3. Issue validation logic

Note: This does NOT test actual Claude API calls to avoid API costs.
"""

import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import directly from modules to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location("prompts", backend_dir / "app" / "services" / "prompts.py")
prompts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompts)

CATEGORIES = prompts.CATEGORIES
ISSUE_TYPES = prompts.ISSUE_TYPES
SEVERITIES = prompts.SEVERITIES
build_extraction_user_prompt = prompts.build_extraction_user_prompt
build_cluster_naming_prompt = prompts.build_cluster_naming_prompt


def test_taxonomy():
    """Test that taxonomy is properly defined."""
    print("Testing taxonomy definitions...")

    assert "TIME_AND_ATTENDANCE" in CATEGORIES
    assert "PAYROLL" in CATEGORIES
    assert "SETTINGS" in CATEGORIES

    assert "punch_in_out" in CATEGORIES["TIME_AND_ATTENDANCE"]
    assert "pay_runs" in CATEGORIES["PAYROLL"]
    assert "employee_registration" in CATEGORIES["SETTINGS"]

    assert "bug" in ISSUE_TYPES
    assert "friction" in ISSUE_TYPES
    assert "feature_request" in ISSUE_TYPES

    assert "critical" in SEVERITIES
    assert "high" in SEVERITIES
    assert "medium" in SEVERITIES
    assert "low" in SEVERITIES

    print("[OK] Taxonomy definitions are valid")


def test_extraction_prompt():
    """Test extraction prompt generation."""
    print("\nTesting extraction prompt generation...")

    sample_ticket = {
        'zendesk_ticket_id': 12345,
        'subject': 'Clock-in button not working',
        'description': 'Employees cannot clock in on Android app',
        'public_comments': 'User: Still having issues after update',
        'internal_notes': 'Agent: Confirmed bug on Android 14',
        'requester_email': 'test@example.com',
        'requester_org_name': 'Test Company',
        'tags': ['mobile', 'android', 'clock-in'],
        'ticket_created_at': '2024-01-15T10:30:00Z'
    }

    prompt = build_extraction_user_prompt(sample_ticket)

    assert "12345" in prompt
    assert "Clock-in button not working" in prompt
    assert "test@example.com" in prompt
    assert "Test Company" in prompt
    assert "mobile, android, clock-in" in prompt
    assert "Employees cannot clock in" in prompt
    assert "Still having issues" in prompt
    assert "Confirmed bug on Android 14" in prompt

    print("[OK] Extraction prompt generation works correctly")


def test_cluster_naming_prompt():
    """Test cluster naming prompt generation."""
    print("\nTesting cluster naming prompt generation...")

    sample_issues = [
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Clock-in button unresponsive on Android 14',
            'representative_quote': 'Button takes 3-4 taps to work'
        },
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Android app clock-in delay after OS update',
            'representative_quote': 'Have to tap multiple times'
        }
    ]

    prompt = build_cluster_naming_prompt(sample_issues)

    assert "TIME_AND_ATTENDANCE" in prompt
    assert "punch_in_out" in prompt
    assert "Number of tickets: 2" in prompt
    assert "Clock-in button unresponsive" in prompt
    assert "Button takes 3-4 taps" in prompt

    print("[OK] Cluster naming prompt generation works correctly")


def test_issue_validation():
    """Test issue validation logic."""
    print("\nTesting issue validation logic...")

    try:
        # Import analyzer module directly to avoid dependency issues
        spec_analyzer = importlib.util.spec_from_file_location("analyzer", backend_dir / "app" / "services" / "analyzer.py")
        analyzer_module = importlib.util.module_from_spec(spec_analyzer)

        # Mock the prompts import in analyzer
        sys.modules['app.services.prompts'] = prompts
        spec_analyzer.loader.exec_module(analyzer_module)

        IssueAnalyzer = analyzer_module.IssueAnalyzer
    except ImportError as e:
        print(f"[SKIP] Skipping validation test (missing dependency: {e})")
        return

    # Create analyzer with dummy API key (won't use it for validation)
    analyzer = IssueAnalyzer(api_key="dummy-key-for-testing")

    # Valid issue
    valid_issue = {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'issue_type': 'bug',
        'severity': 'high',
        'summary': 'Test issue'
    }
    assert analyzer._validate_issue(valid_issue) == True

    # Invalid category
    invalid_category = {
        'category': 'INVALID_CATEGORY',
        'subcategory': 'punch_in_out',
        'issue_type': 'bug',
        'severity': 'high',
        'summary': 'Test issue'
    }
    assert analyzer._validate_issue(invalid_category) == False

    # Invalid subcategory
    invalid_subcategory = {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'invalid_subcategory',
        'issue_type': 'bug',
        'severity': 'high',
        'summary': 'Test issue'
    }
    assert analyzer._validate_issue(invalid_subcategory) == False

    # Invalid issue type
    invalid_issue_type = {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'issue_type': 'invalid_type',
        'severity': 'high',
        'summary': 'Test issue'
    }
    assert analyzer._validate_issue(invalid_issue_type) == False

    # Invalid severity
    invalid_severity = {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'issue_type': 'bug',
        'severity': 'invalid_severity',
        'summary': 'Test issue'
    }
    assert analyzer._validate_issue(invalid_severity) == False

    # Missing summary
    no_summary = {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'issue_type': 'bug',
        'severity': 'high'
    }
    assert analyzer._validate_issue(no_summary) == False

    print("[OK] Issue validation works correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("ISSUE ANALYZER TEST SUITE")
    print("=" * 60)

    try:
        test_taxonomy()
        test_extraction_prompt()
        test_cluster_naming_prompt()
        test_issue_validation()

        print("\n" + "=" * 60)
        print("[OK] ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
