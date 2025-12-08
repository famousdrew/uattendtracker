"""Simple FastAPI wrapper for the MVP."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import Config
from zendesk_client import ZendeskClient
from storage import get_storage
from analyzer import Analyzer
from theme_generator import ThemeGenerator


# Track background sync status
sync_status = {"running": False, "last_result": None}
theme_status = {"running": False, "last_result": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate config
    missing = Config.validate()
    if missing:
        print(f"WARNING: Missing config: {missing}")
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Product Issue Miner",
    description="Extract product issues from Zendesk tickets",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class SyncRequest(BaseModel):
    days: int = 7


class ThemeGenerateRequest(BaseModel):
    mode: str = "full"  # "full" or "incremental"


class SyncResponse(BaseModel):
    status: str
    message: str
    tickets_synced: int = 0


class HealthResponse(BaseModel):
    status: str
    zendesk_configured: bool
    anthropic_configured: bool


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    missing = Config.validate()
    return HealthResponse(
        status="ok",
        zendesk_configured="ZENDESK_SUBDOMAIN" not in missing,
        anthropic_configured="ANTHROPIC_API_KEY" not in missing,
    )


@app.get("/api/test")
def test_connections():
    """Test Zendesk and Claude connections."""
    results = {"zendesk": None, "claude": None}

    # Test Zendesk
    try:
        client = ZendeskClient()
        user = client.test_connection()
        results["zendesk"] = {"ok": True, "user": user["user"]["name"]}
    except Exception as e:
        results["zendesk"] = {"ok": False, "error": str(e)}

    # Test Claude
    try:
        analyzer = Analyzer()
        analyzer.analyze_ticket("Test", "Test ticket")
        results["claude"] = {"ok": True}
    except Exception as e:
        results["claude"] = {"ok": False, "error": str(e)}

    return results


def run_sync_and_analyze(days: int):
    """Background task to sync and analyze tickets."""
    global sync_status
    sync_status["running"] = True
    sync_status["last_result"] = None

    try:
        client = ZendeskClient()
        storage = get_storage()
        analyzer = Analyzer()

        # Sync tickets - fetch ALL tickets in date range (no limit)
        tickets = client.fetch_tickets(days_back=days)
        for ticket in tickets:
            try:
                comments = client.get_ticket_comments(ticket["id"])
            except:
                comments = []
            storage.upsert_ticket(ticket, comments)

        # Analyze
        unanalyzed = storage.get_unanalyzed_tickets()
        issues_count = 0
        for ticket in unanalyzed:
            import json
            comments_text = ""
            if ticket.get("comments_json"):
                try:
                    comments = json.loads(ticket["comments_json"])
                    comments_text = "\n---\n".join([
                        c.get("body", "")[:500] for c in comments if c.get("body")
                    ])
                except:
                    pass

            issues = analyzer.analyze_ticket(
                ticket["subject"] or "",
                ticket["description"] or "",
                comments_text
            )
            for issue in issues:
                storage.save_issue(ticket["zendesk_id"], issue)
                issues_count += 1

        sync_status["last_result"] = {
            "success": True,
            "tickets_synced": len(tickets),
            "tickets_analyzed": len(unanalyzed),
            "issues_extracted": issues_count,
        }
    except Exception as e:
        sync_status["last_result"] = {
            "success": False,
            "error": str(e),
        }
    finally:
        sync_status["running"] = False


@app.post("/api/sync")
def trigger_sync(request: SyncRequest, background_tasks: BackgroundTasks):
    """Trigger a sync and analysis in the background."""
    if sync_status["running"]:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    background_tasks.add_task(run_sync_and_analyze, request.days)
    return {"status": "started", "message": "Sync started in background"}


@app.get("/api/sync/status")
def get_sync_status():
    """Get the status of the last/current sync."""
    return sync_status


@app.get("/api/summary")
def get_summary():
    """Get issue summary statistics."""
    storage = get_storage()
    return storage.get_issue_summary()


@app.get("/api/issues")
def list_issues(limit: int = 50, category: str = None, severity: str = None):
    """List extracted issues."""
    storage = get_storage()
    issues = storage.get_all_issues()

    if category:
        issues = [i for i in issues if i["category"] == category]
    if severity:
        issues = [i for i in issues if i["severity"] == severity]

    return issues[:limit]


@app.get("/api/tickets")
def list_tickets(limit: int = 50):
    """List synced tickets."""
    storage = get_storage()
    return storage.get_all_tickets()[:limit]


@app.delete("/api/data")
def clear_all_data():
    """Clear all tickets and issues from the database."""
    storage = get_storage()
    storage.clear_all()
    return {"status": "ok", "message": "All data cleared"}


# --- Theme Endpoints ---

def run_theme_generation(mode: str):
    """Background task to generate themes."""
    global theme_status
    theme_status["running"] = True
    theme_status["last_result"] = None

    try:
        storage = get_storage()
        generator = ThemeGenerator(storage)
        result = generator.generate_themes(mode=mode)
        theme_status["last_result"] = {"success": True, **result}
    except Exception as e:
        theme_status["last_result"] = {"success": False, "error": str(e)}
    finally:
        theme_status["running"] = False


@app.post("/api/themes/generate")
def trigger_theme_generation(request: ThemeGenerateRequest, background_tasks: BackgroundTasks):
    """Trigger theme generation in the background."""
    if theme_status["running"]:
        raise HTTPException(status_code=409, detail="Theme generation already in progress")

    background_tasks.add_task(run_theme_generation, request.mode)
    return {"status": "started", "message": f"Theme generation started in {request.mode} mode"}


@app.get("/api/themes/status")
def get_theme_status():
    """Get the status of theme generation."""
    return theme_status


@app.get("/api/themes")
def list_themes():
    """List all themes grouped by product area."""
    storage = get_storage()
    themes = storage.get_all_themes()

    # Group themes by product area
    grouped = {}
    for theme in themes:
        area = theme.get("product_area") or "Other"
        if area not in grouped:
            grouped[area] = {"product_area": area, "themes": [], "total_issues": 0}
        grouped[area]["themes"].append(theme)
        grouped[area]["total_issues"] += theme.get("issue_count", 0)

    # Sort by total issues
    result = sorted(grouped.values(), key=lambda x: x["total_issues"], reverse=True)
    return result


@app.get("/api/themes/flat")
def list_themes_flat():
    """List all themes as a flat list."""
    storage = get_storage()
    return storage.get_all_themes()


@app.get("/api/themes/summary")
def get_themes_summary():
    """Get summary statistics for themes."""
    storage = get_storage()
    return storage.get_theme_summary()


@app.get("/api/themes/{theme_id}")
def get_theme_detail(theme_id: int):
    """Get a single theme with its issues."""
    storage = get_storage()
    theme = storage.get_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    issues = storage.get_issues_by_theme(theme_id)
    return {**theme, "issues": issues}


@app.delete("/api/themes")
def clear_themes():
    """Clear all themes (unassigns issues but keeps them)."""
    storage = get_storage()
    storage.clear_themes()
    return {"status": "ok", "message": "All themes cleared"}


# Serve static frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_frontend():
    """Serve the frontend."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not found. API is running at /api/*"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
