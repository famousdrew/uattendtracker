"""Claude-powered issue extraction from tickets."""
import json
from anthropic import Anthropic
from config import Config


SYSTEM_PROMPT = """You are an expert product analyst examining support tickets for a time & attendance / payroll SaaS product.

Your job is to extract product issues from support tickets. For each ticket, identify:
1. Whether it contains a product issue (bug, friction point, feature request, etc.)
2. The category of issue
3. The severity
4. A clear summary

Categories:
- TIME_TRACKING: Clock in/out, timesheets, schedules, overtime
- PAYROLL: Pay calculations, deductions, pay periods, tax
- REPORTING: Reports, exports, analytics
- INTEGRATIONS: Third-party connections, data sync
- USER_MANAGEMENT: Accounts, permissions, authentication
- MOBILE_APP: Mobile-specific issues
- SETTINGS: Configuration, preferences
- OTHER: Anything else

Issue Types:
- bug: Something is broken or not working as expected
- friction: Works but is difficult/confusing to use
- feature_request: User wants new functionality
- documentation_gap: Missing or unclear documentation
- data_issue: Data inconsistency or corruption

Severity:
- critical: Blocking work, data loss, security issue
- high: Major functionality impacted, workaround is difficult
- medium: Noticeable impact but workaround exists
- low: Minor inconvenience

Respond with JSON only. If no product issue is found, return {"issues": []}.
If issues are found, return:
{
    "issues": [
        {
            "category": "CATEGORY",
            "issue_type": "type",
            "severity": "severity",
            "summary": "One-line summary of the issue",
            "detail": "More detailed explanation",
            "confidence": 0.0-1.0
        }
    ]
}"""


class Analyzer:
    """Extract product issues from tickets using Claude."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def analyze_ticket(self, subject: str, description: str, comments: str = None) -> list[dict]:
        """Analyze a single ticket and extract issues."""
        # Build the ticket content
        content = f"Subject: {subject}\n\nDescription:\n{description}"
        if comments:
            content += f"\n\nSupport Thread:\n{comments}"

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": content}
                ]
            )

            # Parse the response
            text = response.content[0].text

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            return data.get("issues", [])

        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response: {e}")
            return []
        except Exception as e:
            print(f"Analysis error: {e}")
            return []


if __name__ == "__main__":
    from rich import print as rprint

    missing = Config.validate()
    if missing:
        rprint(f"[red]Missing config: {missing}[/red]")
        exit(1)

    analyzer = Analyzer()

    # Test with a sample ticket
    test_subject = "Clock in button not working on mobile"
    test_description = """
    When I try to clock in using the mobile app, the button doesn't respond.
    This started happening after the latest update. I have to use the web
    version instead which is really inconvenient for our field workers.
    """

    rprint("[blue]Testing Claude analysis...[/blue]")
    issues = analyzer.analyze_ticket(test_subject, test_description)

    if issues:
        rprint(f"[green]Found {len(issues)} issue(s):[/green]")
        for issue in issues:
            rprint(f"  - [{issue['severity']}] {issue['category']}: {issue['summary']}")
    else:
        rprint("[yellow]No issues extracted[/yellow]")
