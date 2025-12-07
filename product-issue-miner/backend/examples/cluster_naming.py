"""
Example: Generating cluster names with Claude AI

This example demonstrates how to use the IssueAnalyzer to generate
descriptive names for clusters of similar issues.

Usage:
    python examples/cluster_naming.py

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
    """Generate a cluster name for sample issues."""

    print("=" * 70)
    print("CLAUDE AI CLUSTER NAMING DEMO")
    print("=" * 70)

    # Sample cluster of related issues
    issues = [
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Clock-in button unresponsive on Android 14 after OS update',
            'representative_quote': 'Button takes 3-4 taps before it registers'
        },
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Android app clock-in requires multiple tap attempts',
            'representative_quote': 'Have to tap multiple times to clock in'
        },
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Mobile clock-in not working after Android 14 update',
            'representative_quote': 'Updated to Android 14 and now clock-in is broken'
        },
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Clock-in button delayed response on new Android version',
            'representative_quote': 'Button doesn\'t respond right away, have to tap several times'
        },
        {
            'category': 'TIME_AND_ATTENDANCE',
            'subcategory': 'punch_in_out',
            'summary': 'Android 14 users report clock-in touch sensitivity issues',
            'representative_quote': 'Everyone on my team with Android 14 is having this problem'
        }
    ]

    print(f"\nCluster Information:")
    print(f"  Category: {issues[0]['category']}")
    print(f"  Subcategory: {issues[0]['subcategory']}")
    print(f"  Number of issues: {len(issues)}")

    print("\nIssue Summaries:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue['summary']}")

    print("\n" + "-" * 70)
    print("Generating cluster name with Claude AI...")
    print("-" * 70)

    try:
        # Get analyzer instance
        analyzer = get_analyzer()

        # Generate cluster name
        result = analyzer.name_cluster(issues)

        # Display results
        print("\nGenerated Cluster Name:")
        print(f"  {result['cluster_name']}")

        print("\nCluster Summary:")
        summary_lines = result['cluster_summary'].split('. ')
        for line in summary_lines:
            if line:
                print(f"  {line.strip()}.")

        print("\n" + "=" * 70)
        print("Cluster naming complete!")
        print("=" * 70)

    except ValueError as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print("\nMake sure ANTHROPIC_API_KEY is set in your .env file:")
        print("  ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Failed to generate cluster name: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
