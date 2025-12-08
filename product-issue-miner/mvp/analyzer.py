"""Claude-powered issue extraction from tickets."""
import json
from anthropic import Anthropic
from config import Config
from knowledge_base import get_product_context


def build_system_prompt() -> str:
    """Build system prompt with product knowledge."""
    product_context = get_product_context()

    return f"""You are an expert product analyst examining support tickets for uAttend, a time & attendance and payroll SaaS platform.

{product_context}

=== YOUR TASK ===

Analyze support tickets to extract product issues. For each ticket:
1. Determine if it contains a genuine product issue (not just a how-to question)
2. Categorize it accurately based on the product knowledge above
3. Assess severity based on business impact
4. Provide actionable summaries

CATEGORIES (use these exact values):
- TIMECLOCK_HARDWARE: Physical device issues - connectivity, enrollment, display, power
- PUNCH_SYNC: Punches not syncing between device and cloud, missing punches
- TIMECARD: Timecard viewing, editing, approvals, missing time
- SCHEDULING: Employee schedules, shifts, coverage
- PAYROLL: Pay calculations, taxes, deductions, pay periods
- MOBILE_APP: Mobile app specific - login, GPS, notifications
- WEB_DASHBOARD: Web interface issues for managers/admins
- REPORTS: Report generation, exports, analytics
- INTEGRATIONS: Third-party connections, data sync with other systems
- USER_ACCESS: Login, permissions, SSO, password issues
- EMPLOYEE_MANAGEMENT: Adding/removing employees, departments, job codes
- BILLING: Subscription, invoices, pricing
- OTHER: Doesn't fit other categories

ISSUE TYPES:
- bug: Something is broken or not working as expected
- friction: Works but is difficult, confusing, or unintuitive
- feature_request: User wants new functionality that doesn't exist
- data_issue: Data inconsistency, missing data, sync problems
- documentation_gap: User confused due to missing/unclear documentation
- configuration: Settings not working as expected or unclear

SEVERITY (based on business impact):
- critical: Employees can't clock in/out, payroll can't run, data loss
- high: Major functionality broken, significant workaround needed
- medium: Noticeable impact but reasonable workaround exists
- low: Minor inconvenience, cosmetic issues

IMPORTANT GUIDELINES:
- Only extract PRODUCT issues, not general support questions
- A "how do I..." question is NOT an issue unless it reveals a UX problem
- Be specific in summaries - include device models, error messages, affected features
- If multiple issues exist in one ticket, extract each separately
- Confidence should reflect how certain you are this is a real product issue

Respond with JSON only. If no product issue found: {{"issues": []}}

For issues found:
{{
    "issues": [
        {{
            "category": "CATEGORY_FROM_LIST",
            "issue_type": "type_from_list",
            "severity": "severity_from_list",
            "summary": "Specific one-line summary with key details",
            "detail": "Fuller explanation including context, impact, and any error messages",
            "problem_statement": "A natural language description of the user's pain point in their own words. This should capture WHAT the user is trying to do and WHY they can't do it easily. Example: 'I have to manually recreate the same schedule every week because there's no way to copy or set recurring shifts.'",
            "confidence": 0.0-1.0,
            "user_segment": "admin|manager|employee|unknown",
            "platform": "BN6500|MN1000|mobile_app|web|api|unknown",
            "frequency": "one_time|intermittent|consistent|unknown",
            "has_workaround": true|false|null,
            "root_cause_hint": "Brief hypothesis about root cause if apparent",
            "business_impact": "How this affects the customer's operations",
            "related_feature": "Specific feature name like 'GPS punch', 'overtime calc', 'RFID enrollment'"
        }}
    ]
}}

ADDITIONAL CONTEXT GUIDELINES:
- problem_statement: CRITICAL - This is the user's pain point in natural language. Write it as if the user is explaining their frustration. Start with what they're trying to do, then why they can't. Use quotes from the ticket if available. Examples:
  - "I need to copy last week's schedule but there's no copy function, so I spend 2 hours rebuilding it manually every Sunday."
  - "When I try to run payroll, the hours don't match the timecards and I can't figure out why."
  - "My employees keep getting locked out of the mobile app after updating their phones."
- user_segment: Who is experiencing the issue - admin (account owner), manager (supervisor), or employee (regular user)
- platform: Be specific about device model (BN6500, BN6000N, MN1000, CB4000, JR1000, DR1000) or platform (mobile_app, web, api)
- frequency: one_time (happened once), intermittent (sometimes), consistent (always happens)
- has_workaround: Did the support thread mention a workaround the customer could use?
- root_cause_hint: Your hypothesis - could be "network connectivity", "firmware version", "permission settings", "data sync delay", etc.
- business_impact: Describe operational impact - "employees can't clock in", "payroll delayed", "manager can't approve timecards"
- related_feature: Specific feature affected - be granular like "fingerprint enrollment", "break deductions", "PTO accrual"
"""


class Analyzer:
    """Extract product issues from tickets using Claude."""

    def __init__(self):
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self._system_prompt = None

    @property
    def system_prompt(self) -> str:
        """Lazy-load system prompt with knowledge base."""
        if self._system_prompt is None:
            self._system_prompt = build_system_prompt()
        return self._system_prompt

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
                system=self.system_prompt,
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

    rprint("[blue]System prompt preview (first 2000 chars):[/blue]")
    rprint(analyzer.system_prompt[:2000] + "...\n")

    # Test with sample tickets
    test_cases = [
        {
            "subject": "BN6500 not connecting to WiFi",
            "description": """
            Our BN6500 timeclock was working fine but after a power outage it won't connect
            to WiFi anymore. We've tried resetting it but it just shows "Connecting..." and
            never actually connects. Our employees can't clock in.
            """
        },
        {
            "subject": "How do I add a new employee?",
            "description": """
            I'm new to uAttend and need to add some employees. Where do I go to do this?
            """
        },
        {
            "subject": "Payroll hours don't match timecards",
            "description": """
            When I run payroll for last week, the hours shown don't match what's on the
            employees' timecards. For example, John shows 42 hours on his timecard but
            payroll only has 38 hours. This is happening for multiple employees.
            """
        }
    ]

    for test in test_cases:
        rprint(f"\n[yellow]Testing: {test['subject']}[/yellow]")
        issues = analyzer.analyze_ticket(test["subject"], test["description"])

        if issues:
            rprint(f"[green]Found {len(issues)} issue(s):[/green]")
            for issue in issues:
                rprint(f"  [{issue['severity']}] {issue['category']}: {issue['summary']}")
                rprint(f"    Type: {issue['issue_type']}, Confidence: {issue['confidence']}")
        else:
            rprint("[dim]No product issues extracted[/dim]")
