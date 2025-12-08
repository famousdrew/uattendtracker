"""Theme generation service - clusters issues into actionable product themes."""
import json
import re
from collections import defaultdict
from datetime import datetime
from anthropic import Anthropic
from config import Config


# Minimum issues required to form a theme
MIN_THEME_SIZE = 5


class ThemeGenerator:
    """Generate product themes from extracted issues using TF-IDF pre-clustering + LLM synthesis."""

    def __init__(self, storage):
        self.storage = storage
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def generate_themes(self, mode: str = "full") -> dict:
        """
        Generate themes from issues.

        Args:
            mode: "full" to regenerate all themes, "incremental" to only process unthemed issues

        Returns:
            dict with generation results
        """
        # Get issues to process
        if mode == "incremental":
            issues = self.storage.get_unthemed_issues()
            existing_themes = self.storage.get_all_themes()
        else:
            # Full regeneration - clear existing themes
            self.storage.clear_themes()
            issues = self.storage.get_issues_for_theming()
            existing_themes = []

        if not issues:
            return {"status": "no_issues", "themes_created": 0, "issues_themed": 0}

        # Step 1: Pre-cluster issues using keyword extraction
        clusters = self._pre_cluster_issues(issues)

        # Step 2: For each cluster with enough issues, synthesize a theme
        themes_created = 0
        issues_themed = 0

        for cluster_key, cluster_issues in clusters.items():
            if len(cluster_issues) < MIN_THEME_SIZE:
                continue  # Skip small clusters

            # Check if this cluster matches an existing theme (incremental mode)
            matched_theme = None
            if mode == "incremental" and existing_themes:
                matched_theme = self._find_matching_theme(cluster_issues, existing_themes)

            if matched_theme:
                # Add issues to existing theme
                theme_id = matched_theme["id"]
                for issue in cluster_issues:
                    self.storage.assign_issue_to_theme(issue["id"], theme_id)
                    issues_themed += 1
                # Update theme stats
                self._update_theme_stats(theme_id)
            else:
                # Synthesize a new theme using LLM
                theme_data = self._synthesize_theme(cluster_issues)
                if theme_data:
                    theme_id = self.storage.save_theme(theme_data)
                    for issue in cluster_issues:
                        self.storage.assign_issue_to_theme(issue["id"], theme_id)
                        issues_themed += 1
                    themes_created += 1

        return {
            "status": "success",
            "mode": mode,
            "themes_created": themes_created,
            "issues_themed": issues_themed,
            "issues_unthemed": len(issues) - issues_themed,
        }

    def _pre_cluster_issues(self, issues: list[dict]) -> dict[str, list[dict]]:
        """
        Pre-cluster issues based on keywords extracted from problem_statement, summary, and related_feature.
        Uses simple TF-IDF-like approach with key phrases.
        """
        clusters = defaultdict(list)

        for issue in issues:
            # Build text to analyze
            text_parts = [
                issue.get("problem_statement") or "",
                issue.get("summary") or "",
                issue.get("detail") or "",
                issue.get("related_feature") or "",
            ]
            text = " ".join(text_parts).lower()

            # Extract cluster key based on key product concepts
            cluster_key = self._extract_cluster_key(text, issue)
            clusters[cluster_key].append(issue)

        return dict(clusters)

    def _extract_cluster_key(self, text: str, issue: dict) -> str:
        """
        Extract a cluster key from issue text.
        Prioritizes related_feature, then looks for key product terms.
        """
        # First priority: use related_feature if specific enough
        related_feature = (issue.get("related_feature") or "").lower().strip()
        if related_feature and related_feature != "unknown" and len(related_feature) > 3:
            # Normalize the feature name
            return f"feature:{self._normalize_key(related_feature)}"

        # Second priority: look for specific product terms in text
        product_patterns = [
            # Scheduling
            (r'\b(schedule|scheduling|shift|shifts)\b', 'scheduling'),
            (r'\b(copy|duplicate|clone)\s*(schedule|shift)', 'scheduling:copy'),
            (r'\b(recurring|repeat|weekly)\s*(schedule|shift)', 'scheduling:recurring'),
            # Time tracking
            (r'\b(punch|clock\s*in|clock\s*out|clocking)\b', 'punching'),
            (r'\b(gps|location|geofence)\b', 'gps_tracking'),
            (r'\b(fingerprint|biometric|finger)\b', 'biometric'),
            # Payroll
            (r'\b(payroll|pay\s*period|payday)\b', 'payroll'),
            (r'\b(overtime|ot\s*calc|ot\s*hours)\b', 'overtime'),
            (r'\b(pto|vacation|sick\s*time|time\s*off)\b', 'pto'),
            # Hardware
            (r'\b(bn6500|bn6000|timeclock|time\s*clock)\b', 'timeclock_device'),
            (r'\b(wifi|network|connect|offline)\b', 'connectivity'),
            # Mobile
            (r'\b(mobile\s*app|app\s*crash|ios|android)\b', 'mobile_app'),
            # Reports
            (r'\b(report|export|csv|excel)\b', 'reports'),
            # Timecard
            (r'\b(timecard|time\s*card|edit\s*time|missing\s*time)\b', 'timecard'),
            # User management
            (r'\b(login|password|locked\s*out|access)\b', 'user_access'),
            (r'\b(employee|add\s*user|remove\s*user)\b', 'employee_management'),
        ]

        for pattern, key in product_patterns:
            if re.search(pattern, text):
                return f"topic:{key}"

        # Fall back to category
        category = (issue.get("category") or "OTHER").lower()
        return f"category:{category}"

    def _normalize_key(self, text: str) -> str:
        """Normalize a string for use as a cluster key."""
        # Remove special chars, collapse whitespace
        text = re.sub(r'[^a-z0-9\s]', '', text.lower())
        text = re.sub(r'\s+', '_', text.strip())
        return text[:50]  # Limit length

    def _find_matching_theme(self, cluster_issues: list[dict], existing_themes: list[dict]) -> dict | None:
        """
        Find an existing theme that matches this cluster.
        Uses simple keyword overlap for now.
        """
        # Build keyword set from cluster issues
        cluster_keywords = set()
        for issue in cluster_issues:
            text = f"{issue.get('problem_statement', '')} {issue.get('summary', '')} {issue.get('related_feature', '')}"
            words = re.findall(r'\b[a-z]{3,}\b', text.lower())
            cluster_keywords.update(words)

        best_match = None
        best_score = 0

        for theme in existing_themes:
            # Build keyword set from theme
            theme_text = f"{theme.get('name', '')} {theme.get('summary', '')} {theme.get('feature_workflow', '')}"
            theme_keywords = set(re.findall(r'\b[a-z]{3,}\b', theme_text.lower()))

            # Calculate Jaccard similarity
            if theme_keywords:
                intersection = len(cluster_keywords & theme_keywords)
                union = len(cluster_keywords | theme_keywords)
                score = intersection / union if union > 0 else 0

                if score > best_score and score > 0.3:  # 30% threshold
                    best_score = score
                    best_match = theme

        return best_match

    def _synthesize_theme(self, issues: list[dict]) -> dict | None:
        """
        Use Claude to synthesize a theme from a cluster of issues.
        Returns theme data ready to save.
        """
        # Build context for Claude
        issues_text = []
        quotes = []
        customers = set()
        severities = []
        dates = []

        for i, issue in enumerate(issues[:30]):  # Limit to 30 for context window
            problem = issue.get("problem_statement") or issue.get("summary") or ""
            detail = issue.get("detail") or ""
            business_impact = issue.get("business_impact") or ""

            issues_text.append(f"""
Issue {i+1}:
- Problem: {problem}
- Detail: {detail}
- Business Impact: {business_impact}
- Feature: {issue.get('related_feature', 'unknown')}
- Severity: {issue.get('severity', 'unknown')}
""")

            # Collect quotes (from problem statements that look like quotes)
            if problem and len(problem) > 20:
                quotes.append(problem)

            # Track unique customers
            if issue.get("requester_email"):
                customers.add(issue["requester_email"])

            severities.append(issue.get("severity", "medium"))
            if issue.get("extracted_at"):
                dates.append(issue["extracted_at"])

        prompt = f"""Analyze these {len(issues)} related product issues and create a theme summary for product managers.

ISSUES:
{"".join(issues_text)}

Create a JSON response with:
{{
    "name": "Short, specific theme name (5-8 words max). Examples: 'Schedule Copy & Recurring Shifts Missing', 'GPS Punch Location Accuracy Issues'",
    "product_area": "Infer the broad product area. Examples: 'Scheduling', 'Time Tracking', 'Payroll', 'Mobile App', 'Timeclock Hardware', 'Reports', 'User Management'",
    "summary": "2-3 sentence PM-friendly summary explaining WHAT users are struggling with and WHY it matters. Focus on the pattern across issues.",
    "specific_feedback": ["Array of 3-5 specific, distinct feedback points synthesized from the issues. Each should be actionable and specific."],
    "feature_workflow": "The specific feature or workflow affected. Example: 'Scheduling > Weekly View > Copy Function'",
    "representative_quotes": ["2-3 actual quotes from the problem statements that best represent user frustration"]
}}

Be specific and actionable. Avoid generic descriptions."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text

            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            theme_data = json.loads(text.strip())

            # Add computed fields
            theme_data["issue_count"] = len(issues)
            theme_data["unique_customers"] = len(customers)
            theme_data["first_seen"] = min(dates) if dates else datetime.utcnow().isoformat()
            theme_data["last_seen"] = max(dates) if dates else datetime.utcnow().isoformat()

            return theme_data

        except Exception as e:
            print(f"Theme synthesis error: {e}")
            # Return a basic theme if LLM fails
            return {
                "name": f"Issues: {issues[0].get('related_feature', 'Unknown')}",
                "product_area": issues[0].get("category", "OTHER"),
                "summary": f"Cluster of {len(issues)} related issues",
                "specific_feedback": [],
                "representative_quotes": quotes[:3],
                "feature_workflow": issues[0].get("related_feature", "Unknown"),
                "issue_count": len(issues),
                "unique_customers": len(customers),
                "first_seen": min(dates) if dates else datetime.utcnow().isoformat(),
                "last_seen": max(dates) if dates else datetime.utcnow().isoformat(),
            }

    def _update_theme_stats(self, theme_id: int):
        """Update theme statistics after adding new issues."""
        issues = self.storage.get_issues_by_theme(theme_id)
        theme = self.storage.get_theme(theme_id)

        if not theme:
            return

        customers = set()
        dates = []
        for issue in issues:
            if issue.get("requester_email"):
                customers.add(issue["requester_email"])
            if issue.get("extracted_at"):
                dates.append(issue["extracted_at"])

        theme["issue_count"] = len(issues)
        theme["unique_customers"] = len(customers)
        if dates:
            theme["last_seen"] = max(dates)

        self.storage.update_theme(theme_id, theme)


if __name__ == "__main__":
    from rich import print as rprint
    from storage import get_storage

    missing = Config.validate()
    if missing:
        rprint(f"[red]Missing config: {missing}[/red]")
        exit(1)

    storage = get_storage()
    generator = ThemeGenerator(storage)

    rprint("[blue]Generating themes (full mode)...[/blue]")
    result = generator.generate_themes(mode="full")
    rprint(f"[green]Result: {result}[/green]")

    themes = storage.get_all_themes()
    rprint(f"\n[yellow]Generated {len(themes)} themes:[/yellow]")
    for theme in themes:
        rprint(f"\n[bold]{theme['name']}[/bold] ({theme['issue_count']} issues)")
        rprint(f"  Product Area: {theme['product_area']}")
        rprint(f"  Summary: {theme['summary']}")
        if theme.get("specific_feedback"):
            rprint("  Feedback:")
            for fb in theme["specific_feedback"][:3]:
                rprint(f"    • {fb}")
