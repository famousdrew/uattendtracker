"""
Debug sync test endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timedelta
import traceback

from app.api.deps import get_db, verify_password
from app.models import Ticket

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/sync-test")
async def debug_sync_test(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """Test sync flow step by step."""
    from app.services.zendesk import get_zendesk_client
    from app.services.sync import parse_zendesk_datetime
    from app.config import settings

    results = {"steps": [], "tickets_processed": 0, "errors": []}
    client = get_zendesk_client()

    try:
        await client._ensure_client()
        results["steps"].append({"step": 1, "name": "Init client", "ok": True})

        start_date = datetime.utcnow() - timedelta(days=7)
        query = f"type:ticket updated>{start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        if settings.ZENDESK_BRAND_ID:
            query = f"{query} brand:{settings.ZENDESK_BRAND_ID}"
        results["steps"].append({"step": 2, "query": query, "ok": True})

        search_resp = await client.search_tickets(query, page=1, per_page=3)
        ticket_list = search_resp.get("results", [])
        results["steps"].append({
            "step": 3,
            "name": "Search",
            "ok": True,
            "total": search_resp.get("count", 0),
            "fetched": len(ticket_list)
        })

        for td in ticket_list[:2]:
            tid = td.get("id")
            try:
                ft = await client.get_ticket_with_comments(tid)
                ti = ft["ticket"]
                int_notes = client.format_comments(ft.get("internal_notes", []))
                pub_com = client.format_comments(ft.get("public_comments", []))
                cr = parse_zendesk_datetime(ti.get("created_at"))
                up = parse_zendesk_datetime(ti.get("updated_at"))

                stmt = insert(Ticket).values(
                    zendesk_ticket_id=ti["id"],
                    subject=ti.get("subject"),
                    description=ti.get("description"),
                    internal_notes=int_notes,
                    public_comments=pub_com,
                    requester_email=None,
                    requester_org_name=None,
                    zendesk_org_id=ti.get("organization_id"),
                    tags=ti.get("tags", []),
                    status=ti.get("status"),
                    priority=ti.get("priority"),
                    ticket_created_at=cr,
                    ticket_updated_at=up,
                    synced_at=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=["zendesk_ticket_id"],
                    set_={
                        "subject": ti.get("subject"),
                        "synced_at": datetime.utcnow()
                    }
                )

                await db.execute(stmt)
                results["tickets_processed"] += 1
                results["steps"].append({
                    "step": f"4.{results['tickets_processed']}",
                    "ticket": tid,
                    "ok": True
                })
            except Exception as e:
                results["errors"].append({"ticket": tid, "error": str(e)})

        await db.commit()
        results["steps"].append({"step": 5, "name": "Commit", "ok": True})

        count_q = select(func.count()).select_from(Ticket)
        count_r = await db.execute(count_q)
        total = count_r.scalar_one()
        results["steps"].append({"step": 6, "total_in_db": total, "ok": True})

    except Exception as e:
        results["error"] = str(e)
        results["tb"] = traceback.format_exc()
    finally:
        await client.close()

    return results
