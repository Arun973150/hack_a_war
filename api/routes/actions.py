import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from config import settings
from org_context.models.database import (
    list_action_items,
    update_action_status,
    update_action_jira_ticket,
)

logger = structlog.get_logger()
router = APIRouter()


class UpdateActionStatusRequest(BaseModel):
    status: str   # open | in_progress | completed | waived
    note: Optional[str] = None


class JiraExportRequest(BaseModel):
    action_ids: list[str]
    project_key: Optional[str] = None


@router.get("/")
async def list_actions(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 50,
):
    """List action items from PostgreSQL with optional filters."""
    items = list_action_items(priority=priority, status=status, owner=owner, limit=limit)
    return {
        "action_items": [
            {
                "action_id": i.action_id,
                "title": i.title,
                "description": i.description,
                "owner": i.owner,
                "deadline": i.deadline,
                "priority": i.priority,
                "effort_days": i.effort_days,
                "compliance_risk_score": i.compliance_risk_score,
                "status": i.status,
                "jira_ticket_id": i.jira_ticket_id,
                "source_obligation_ids": i.source_obligation_ids,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
        "total": len(items),
        "filters": {"priority": priority, "status": status, "owner": owner},
    }


@router.patch("/{action_id}/status")
async def update_status(action_id: str, request: UpdateActionStatusRequest):
    """Update the status of an action item in PostgreSQL."""
    valid_statuses = ["open", "in_progress", "completed", "waived"]
    if request.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    updated = update_action_status(action_id, request.status)
    if not updated:
        raise HTTPException(404, f"Action item '{action_id}' not found")

    logger.info("action_status_updated", action_id=action_id, status=request.status)
    return {"action_id": action_id, "status": request.status, "updated": True}


@router.post("/export/jira")
async def export_to_jira(request: JiraExportRequest):
    """
    Export action items to Jira as tickets.
    Requires JIRA_BASE_URL, JIRA_API_TOKEN, JIRA_EMAIL in .env
    """
    if not settings.jira_base_url or not settings.jira_api_token:
        raise HTTPException(400, "Jira credentials not configured")

    project_key = request.project_key or settings.jira_project_key
    created_tickets = []

    # Fetch real action items from DB
    all_items = list_action_items(limit=500)
    items_by_id = {i.action_id: i for i in all_items}

    PRIORITY_MAP = {
        "CRITICAL": "Highest",
        "HIGH": "High",
        "MEDIUM": "Medium",
        "LOW": "Low",
    }

    async with httpx.AsyncClient() as client:
        for action_id in request.action_ids:
            item = items_by_id.get(action_id)
            if not item:
                logger.warning("action_item_not_found_for_jira", action_id=action_id)
                continue

            jira_priority = PRIORITY_MAP.get((item.priority or "").upper(), "Medium")
            description_text = item.description or item.title or ""

            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": f"[Compliance] {item.title}",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [{"type": "paragraph", "content": [
                            {"type": "text", "text": description_text}
                        ]}]
                    },
                    "issuetype": {"name": "Task"},
                    "priority": {"name": jira_priority},
                }
            }

            try:
                response = await client.post(
                    f"{settings.jira_base_url}/rest/api/3/issue",
                    json=payload,
                    auth=(settings.jira_email, settings.jira_api_token),
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                )
                if response.status_code == 201:
                    ticket_data = response.json()
                    jira_key = ticket_data["key"]
                    update_action_jira_ticket(action_id, jira_key)
                    created_tickets.append({
                        "action_id": action_id,
                        "jira_key": jira_key,
                        "jira_url": f"{settings.jira_base_url}/browse/{jira_key}",
                    })
                    logger.info("jira_ticket_created", action_id=action_id, jira_key=jira_key)
                else:
                    logger.error("jira_create_failed", action_id=action_id,
                                 status=response.status_code, body=response.text[:300])
            except Exception as e:
                logger.error("jira_export_error", action_id=action_id, error=str(e))

    return {"created_tickets": created_tickets, "total": len(created_tickets)}
