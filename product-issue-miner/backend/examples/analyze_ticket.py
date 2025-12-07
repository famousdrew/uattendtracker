"""
Example: Analyzing a single ticket with Claude AI

This example demonstrates how to use the IssueAnalyzer to extract
product issues from a support ticket.

Usage:
    python examples/analyze_ticket.py

Requirements:
    - ANTHROPIC_API_KEY must be set in .env file
    - anthropic package must be installed (pip install -r requirements.txt)
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services import get_analyzer


def main():
    """Analyze a sample ticket and display results."""

    print("=" * 70)
    print("CLAUDE AI ISSUE EXTRACTION DEMO")
    print("=" * 70)

    # Sample ticket data
    ticket = {
        'zendesk_ticket_id': 12345,
        'subject': 'Employees unable to clock in - Android app',
        'description': '''
We have multiple employees who updated their phones to Android 14
and now they're having trouble clocking in. The button seems to
work sometimes but usually they have to tap it 3-4 times before
it registers. This is causing delays and frustration.
        ''',
        'public_comments': '''
User comment 1: "Still having this issue after the latest app update"
User comment 2: "My whole team is having the same problem"
        ''',
        'internal_notes': '''
Agent note: Confirmed this is a bug affecting Android 14 users.
Engineering is aware and working on a fix.
        ''',
        'requester_email': 'manager@acmecorp.com',
        'requester_org_name': 'Acme Corporation',
        'tags': ['mobile', 'android', 'clock-in', 'bug'],
        'ticket_created_at': '2024-01-15T10:30:00Z'
    }

    print("\nTicket Information:")
    print(f"  ID: {ticket['zendesk_ticket_id']}")
    print(f"  Subject: {ticket['subject']}")
    print(f"  Organization: {ticket['requester_org_name']}")
    print(f"  Tags: {', '.join(ticket['tags'])}")

    print("\n" + "-" * 70)
    print("Analyzing ticket with Claude AI...")
    print("-" * 70)

    try:
        # Get analyzer instance
        analyzer = get_analyzer()

        # Extract issues
        result = analyzer.extract_issues(ticket)

        # Display results
        print("\nAnalysis Results:")
        print(f"  No product issue: {result['no_product_issue']}")

        if result['skip_reason']:
            print(f"  Skip reason: {result['skip_reason']}")

        if result['issues']:
            print(f"\n  Found {len(result['issues'])} issue(s):\n")

            for i, issue in enumerate(result['issues'], 1):
                print(f"  Issue #{i}:")
                print(f"    Category: {issue['category']}")
                print(f"    Subcategory: {issue['subcategory']}")
                print(f"    Type: {issue['issue_type']}")
                print(f"    Severity: {issue['severity']}")
                print(f"    Confidence: {issue.get('confidence', 'N/A')}")
                print(f"    Summary: {issue['summary']}")

                if issue.get('detail'):
                    print(f"    Detail: {issue['detail'][:100]}...")

                if issue.get('representative_quote'):
                    print(f"    Quote: \"{issue['representative_quote']}\"")

                print()
        else:
            print("\n  No product issues found in this ticket.")

        print("=" * 70)
        print("Analysis complete!")
        print("=" * 70)

    except ValueError as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print("\nMake sure ANTHROPIC_API_KEY is set in your .env file:")
        print("  ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Failed to analyze ticket: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
