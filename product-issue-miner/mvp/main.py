#!/usr/bin/env python3
"""
Product Issue Miner - MVP

A simple CLI tool to:
1. Fetch tickets from Zendesk
2. Store them locally
3. Analyze with Claude
4. Generate reports
"""
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import Config
from zendesk_client import ZendeskClient
from storage import get_storage
from analyzer import Analyzer

console = Console()


def cmd_test(args):
    """Test connections to Zendesk and Claude."""
    console.print("\n[bold blue]Testing Connections[/bold blue]\n")

    # Check config
    missing = Config.validate()
    if missing:
        console.print(f"[red]Missing environment variables: {missing}[/red]")
        console.print("Copy .env.example to .env and fill in your values")
        return False

    # Test Zendesk
    console.print("Zendesk: ", end="")
    try:
        client = ZendeskClient()
        user = client.test_connection()
        console.print(f"[green]OK[/green] - Connected as {user['user']['name']}")
    except Exception as e:
        console.print(f"[red]FAILED[/red] - {e}")
        return False

    # Test Claude
    console.print("Claude:  ", end="")
    try:
        analyzer = Analyzer()
        issues = analyzer.analyze_ticket("Test", "This is a test ticket")
        console.print("[green]OK[/green] - API responding")
    except Exception as e:
        console.print(f"[red]FAILED[/red] - {e}")
        return False

    console.print("\n[green]All connections working![/green]")
    return True


def cmd_sync(args):
    """Sync tickets from Zendesk."""
    missing = Config.validate()
    if missing:
        console.print(f"[red]Missing config: {missing}[/red]")
        return

    client = ZendeskClient()
    storage = get_storage()

    console.print(f"\nSyncing tickets from last {args.days} days...\n")

    console.print("Fetching tickets...")
    tickets = client.fetch_tickets(days_back=args.days, limit=args.limit)
    console.print(f"Found {len(tickets)} tickets")

    for i, ticket in enumerate(tickets):
        console.print(f"  Processing {i+1}/{len(tickets)}: #{ticket['id']}")

        # Fetch comments
        try:
            comments = client.get_ticket_comments(ticket["id"])
        except Exception:
            comments = []

        # Store ticket
        storage.upsert_ticket(ticket, comments)

    summary = storage.get_issue_summary()
    console.print(f"\nSync complete!")
    console.print(f"Total tickets in database: {summary['total_tickets']}")


def cmd_analyze(args):
    """Analyze unprocessed tickets with Claude."""
    missing = Config.validate()
    if missing:
        console.print(f"[red]Missing config: {missing}[/red]")
        return

    storage = get_storage()
    analyzer = Analyzer()

    # Get unanalyzed tickets
    tickets = storage.get_unanalyzed_tickets()

    if not tickets:
        console.print("[yellow]No unanalyzed tickets found. Run 'sync' first.[/yellow]")
        return

    console.print(f"\nAnalyzing {len(tickets)} tickets...\n")

    total_issues = 0

    for i, ticket in enumerate(tickets):
        subject = (ticket['subject'] or '')[:40]
        console.print(f"  [{i+1}/{len(tickets)}] #{ticket['zendesk_id']}: {subject}...")

        # Parse comments
        comments_text = ""
        if ticket.get("comments_json"):
            try:
                comments = json.loads(ticket["comments_json"])
                comments_text = "\n---\n".join([
                    c.get("body", "")[:500] for c in comments if c.get("body")
                ])
            except:
                pass

        # Analyze
        issues = analyzer.analyze_ticket(
            ticket["subject"] or "",
            ticket["description"] or "",
            comments_text
        )

        # Save issues
        for issue in issues:
            storage.save_issue(ticket["zendesk_id"], issue)
            total_issues += 1

        if issues:
            console.print(f"    -> Found {len(issues)} issue(s)")

    console.print(f"\nAnalysis complete!")
    console.print(f"Extracted {total_issues} issues from {len(tickets)} tickets")


def cmd_report(args):
    """Generate a summary report."""
    storage = get_storage()
    summary = storage.get_issue_summary()

    console.print("\n")
    console.print(Panel.fit(
        f"[bold]Tickets:[/bold] {summary['total_tickets']}  |  [bold]Issues:[/bold] {summary['total_issues']}",
        title="Product Issue Report",
        border_style="blue"
    ))

    if summary["total_issues"] == 0:
        console.print("\n[yellow]No issues found. Run 'sync' then 'analyze' first.[/yellow]")
        return

    # By Severity
    table = Table(title="Issues by Severity")
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")

    severity_colors = {"critical": "red", "high": "orange1", "medium": "yellow", "low": "green"}
    for row in summary["by_severity"]:
        color = severity_colors.get(row["severity"], "white")
        table.add_row(f"[{color}]{row['severity']}[/{color}]", str(row["count"]))
    console.print(table)

    # By Category
    table = Table(title="Issues by Category")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    for row in summary["by_category"]:
        table.add_row(row["category"], str(row["count"]))
    console.print(table)

    # By Type
    table = Table(title="Issues by Type")
    table.add_column("Type", style="bold")
    table.add_column("Count", justify="right")
    for row in summary["by_type"]:
        table.add_row(row["issue_type"], str(row["count"]))
    console.print(table)

    # Recent Issues
    if args.details:
        issues = storage.get_all_issues()[:20]
        table = Table(title="Recent Issues (Top 20)")
        table.add_column("Ticket", style="dim", width=8)
        table.add_column("Category", width=15)
        table.add_column("Severity", width=10)
        table.add_column("Summary", width=50)

        for issue in issues:
            sev_color = severity_colors.get(issue["severity"], "white")
            table.add_row(
                f"#{issue['zendesk_id']}",
                issue["category"],
                f"[{sev_color}]{issue['severity']}[/{sev_color}]",
                (issue["summary"] or "")[:50]
            )
        console.print(table)


def cmd_clear(args):
    """Clear stored data."""
    storage = get_storage()

    if args.issues:
        storage.clear_issues()
        console.print("[green]Cleared all issues. Tickets preserved.[/green]")
    else:
        import os
        if os.path.exists("mvp_data.db"):
            os.remove("mvp_data.db")
        console.print("[green]Database cleared.[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Product Issue Miner - Extract product issues from Zendesk tickets"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # test
    subparsers.add_parser("test", help="Test Zendesk and Claude connections")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync tickets from Zendesk")
    sync_parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    sync_parser.add_argument("--limit", type=int, default=100, help="Max tickets (default: 100)")

    # analyze
    subparsers.add_parser("analyze", help="Analyze tickets with Claude")

    # report
    report_parser = subparsers.add_parser("report", help="Generate summary report")
    report_parser.add_argument("--details", action="store_true", help="Show detailed issue list")

    # clear
    clear_parser = subparsers.add_parser("clear", help="Clear stored data")
    clear_parser.add_argument("--issues", action="store_true", help="Only clear issues, keep tickets")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "test": cmd_test,
        "sync": cmd_sync,
        "analyze": cmd_analyze,
        "report": cmd_report,
        "clear": cmd_clear,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
