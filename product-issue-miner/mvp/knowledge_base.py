"""Fetch and manage knowledge base from uAttend Help Center."""
import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path


HELP_CENTER_BASE = "https://uattend.zendesk.com/api/v2/help_center/en-us"
CACHE_FILE = Path(__file__).parent / "data" / "knowledge_base.json"
CACHE_DURATION_DAYS = 7


def fetch_categories() -> list[dict]:
    """Fetch all help center categories."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{HELP_CENTER_BASE}/categories.json")
        response.raise_for_status()
        return response.json().get("categories", [])


def fetch_sections() -> list[dict]:
    """Fetch all help center sections."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{HELP_CENTER_BASE}/sections.json")
        response.raise_for_status()
        return response.json().get("sections", [])


def fetch_articles() -> list[dict]:
    """Fetch all help center articles with pagination."""
    articles = []
    url = f"{HELP_CENTER_BASE}/articles.json?per_page=100"

    with httpx.Client(timeout=30.0) as client:
        while url:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            articles.extend(data.get("articles", []))
            url = data.get("next_page")

    return articles


def strip_html(html: str) -> str:
    """Simple HTML stripping - removes tags."""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def build_knowledge_base() -> dict:
    """Build a structured knowledge base from the help center."""
    print("Fetching help center content...")

    categories = fetch_categories()
    sections = fetch_sections()
    articles = fetch_articles()

    # Build category lookup
    cat_lookup = {c["id"]: c["name"] for c in categories}

    # Build section lookup with category
    section_lookup = {}
    for s in sections:
        cat_name = cat_lookup.get(s["category_id"], "Other")
        section_lookup[s["id"]] = {
            "name": s["name"],
            "category": cat_name
        }

    # Process articles
    processed_articles = []
    for article in articles:
        section_info = section_lookup.get(article["section_id"], {"name": "General", "category": "Other"})

        # Extract plain text content (truncate for prompt efficiency)
        body_text = strip_html(article.get("body", ""))[:1000]

        processed_articles.append({
            "title": article["title"],
            "category": section_info["category"],
            "section": section_info["name"],
            "summary": body_text[:300],  # Short summary for context
            "url": article.get("html_url", "")
        })

    # Group by category for easy reference
    by_category = {}
    for article in processed_articles:
        cat = article["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(article["title"])

    knowledge_base = {
        "fetched_at": datetime.utcnow().isoformat(),
        "categories": list(cat_lookup.values()),
        "sections": [s["name"] for s in sections],
        "article_count": len(processed_articles),
        "articles_by_category": by_category,
        "articles": processed_articles
    }

    return knowledge_base


def save_knowledge_base(kb: dict):
    """Save knowledge base to cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(kb, f, indent=2)
    print(f"Saved {kb['article_count']} articles to {CACHE_FILE}")


def load_knowledge_base() -> dict | None:
    """Load knowledge base from cache if fresh enough."""
    if not CACHE_FILE.exists():
        return None

    try:
        with open(CACHE_FILE) as f:
            kb = json.load(f)

        # Check if cache is fresh
        fetched_at = datetime.fromisoformat(kb["fetched_at"])
        if datetime.utcnow() - fetched_at > timedelta(days=CACHE_DURATION_DAYS):
            print("Knowledge base cache expired")
            return None

        return kb
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None


def get_knowledge_base(force_refresh: bool = False) -> dict:
    """Get knowledge base, fetching if needed."""
    if not force_refresh:
        kb = load_knowledge_base()
        if kb:
            return kb

    kb = build_knowledge_base()
    save_knowledge_base(kb)
    return kb


def get_product_context() -> str:
    """Generate a concise product context string for the LLM."""
    kb = get_knowledge_base()

    # Build a structured context
    context_parts = [
        "=== uAttend Product Knowledge Base ===",
        "",
        "uAttend is a time & attendance and payroll SaaS platform with physical timeclocks.",
        "",
        "PRODUCT AREAS:",
    ]

    for category, articles in kb["articles_by_category"].items():
        context_parts.append(f"\n{category}:")
        for title in articles[:10]:  # Limit to top 10 per category
            context_parts.append(f"  - {title}")

    context_parts.append("\n\nKEY FEATURES:")
    context_parts.append("- Physical timeclocks: BN series, MN series, CB series, JR series, DR series")
    context_parts.append("- Punch methods: PIN, RFID cards, key fobs, fingerprint, facial recognition")
    context_parts.append("- Mobile app for remote clock in/out")
    context_parts.append("- Web dashboard for managers and admins")
    context_parts.append("- Timecard management and editing")
    context_parts.append("- Payroll processing with tax calculations")
    context_parts.append("- Employee scheduling")
    context_parts.append("- Reports and exports")
    context_parts.append("- Integrations with payroll providers")

    context_parts.append("\n\nCOMMON ISSUE PATTERNS:")
    context_parts.append("- Timeclock connectivity (WiFi, ethernet, static IP)")
    context_parts.append("- Employee enrollment on devices (fingerprint, face, RFID)")
    context_parts.append("- Punch not syncing between device and cloud")
    context_parts.append("- Timecard discrepancies and missing punches")
    context_parts.append("- Mobile app login or GPS issues")
    context_parts.append("- Payroll calculation errors")
    context_parts.append("- Report generation or export problems")
    context_parts.append("- User permission and access issues")

    return "\n".join(context_parts)


if __name__ == "__main__":
    from rich import print as rprint

    rprint("[blue]Building knowledge base from uAttend Help Center...[/blue]")
    kb = get_knowledge_base(force_refresh=True)

    rprint(f"\n[green]Categories:[/green] {kb['categories']}")
    rprint(f"[green]Total Articles:[/green] {kb['article_count']}")

    rprint("\n[yellow]Articles by Category:[/yellow]")
    for cat, articles in kb["articles_by_category"].items():
        rprint(f"  {cat}: {len(articles)} articles")

    rprint("\n[blue]Product Context Preview:[/blue]")
    context = get_product_context()
    rprint(context[:2000] + "...")
