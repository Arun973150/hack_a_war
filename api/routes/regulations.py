import json
import asyncio
import structlog
import httpx
import feedparser
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional

from agents.graph import ComplianceOrchestrator
from agents.state import ComplianceWorkflowState
from knowledge.vectors.qdrant_store import RegulatoryVectorStore
from api import progress_store
from org_context.models.database import create_action_item, list_action_items, update_action_jira_ticket
from config import settings

logger = structlog.get_logger()
router = APIRouter()

AGENT_ORDER = ["scanner", "extractor", "impact_analyst", "action_planner", "validator"]


class ProcessDocumentRequest(BaseModel):
    document_id: str
    raw_text: str
    source_url: str
    jurisdiction: str
    regulatory_body: str
    document_type: str
    published_date: str


class SearchRequest(BaseModel):
    query: str
    jurisdiction: Optional[str] = None
    regulatory_body: Optional[str] = None
    limit: int = 10


def _serialize_result(
    state: ComplianceWorkflowState,
    auto_slack_sent: bool = False,
    auto_jira_tickets: list | None = None,
) -> dict:
    return {
        "document_id": state.document_id,
        "is_relevant": state.is_relevant,
        "relevance_score": state.relevance_score,
        "sector": state.sector,
        "obligations": [o.dict() for o in state.obligations],
        "affected_business_units": state.affected_business_units,
        "gaps": [g.dict() for g in state.gaps],
        "overall_risk_score": state.overall_risk_score,
        "jurisdiction_conflicts": state.jurisdiction_conflicts,
        "impact_summary": state.impact_summary,
        "action_items": [a.dict() for a in state.action_items],
        "security_advisories": [a.dict() for a in (state.security_advisories or [])],
        "validation": state.validation.dict() if state.validation else None,
        "error": state.error,
        # Auto-trigger results
        "auto_slack_sent": auto_slack_sent,
        "auto_jira_tickets": auto_jira_tickets or [],
    }


@router.post("/process")
async def process_regulation(
    request: ProcessDocumentRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger the full 5-agent compliance analysis pipeline.
    Returns immediately — stream progress via GET /api/v1/stream/{document_id}.
    """
    progress_store.clear(request.document_id)

    def run_pipeline():
        try:
            orchestrator = ComplianceOrchestrator()
            initial_state = ComplianceWorkflowState(
                document_id=request.document_id,
                raw_text=request.raw_text,
                source_url=request.source_url,
                jurisdiction=request.jurisdiction,
                regulatory_body=request.regulatory_body,
                document_type=request.document_type,
                published_date=request.published_date,
            )
            config = {"configurable": {"thread_id": request.document_id}}

            # Stream per-node updates from LangGraph
            for update in orchestrator._graph.stream(
                initial_state, config=config, stream_mode="updates"
            ):
                for node_name, node_state in update.items():
                    if node_name == "__end__":
                        continue
                    step_idx = AGENT_ORDER.index(node_name) if node_name in AGENT_ORDER else -1

                    # Extract key info from node output
                    logs = _extract_node_logs(node_name, node_state)

                    progress_store.publish_event(request.document_id, {
                        "type": "agent_done",
                        "node": node_name,
                        "step": step_idx,
                        "logs": logs,
                    })
                    logger.info("pipeline_node_done", doc=request.document_id, node=node_name)

            # Retrieve final state from checkpointer
            final = orchestrator._graph.get_state(config)
            if final and final.values:
                state = ComplianceWorkflowState(**final.values) if isinstance(final.values, dict) else final.values

                # Persist action items to PostgreSQL so Jira export can find them
                _save_action_items(state)

                # Snapshot obligations for regulation diff engine
                _snapshot_obligations(state, request)

                # Auto-trigger Slack + Jira for high-risk results
                auto_slack, auto_jira = _auto_notify(state, request)

                if auto_slack:
                    progress_store.publish_event(request.document_id, {
                        "type": "agent_done", "node": "auto_notify", "step": -1,
                        "logs": [
                            f"Auto-alert sent to Slack · risk {state.overall_risk_score}/10",
                            f"Auto-created {len(auto_jira)} Jira ticket(s) for CRITICAL actions",
                        ] if auto_jira else [
                            f"Auto-alert sent to Slack · risk {state.overall_risk_score}/10",
                        ],
                    })

                progress_store.publish_result(
                    request.document_id,
                    _serialize_result(state, auto_slack_sent=auto_slack, auto_jira_tickets=auto_jira),
                )
            else:
                progress_store.publish_result(request.document_id, {"error": "No final state"})

        except Exception as e:
            logger.error("pipeline_failed", doc=request.document_id, error=str(e))
            progress_store.publish_event(request.document_id, {
                "type": "error", "message": str(e)
            })
            progress_store.publish_result(request.document_id, {"error": str(e)})

    background_tasks.add_task(run_pipeline)
    return {"status": "processing", "document_id": request.document_id}


def _save_action_items(state) -> None:
    """Persist pipeline-generated action items to PostgreSQL (upsert by action_id)."""
    try:
        action_items = getattr(state, "action_items", None) or (state.get("action_items") if isinstance(state, dict) else [])
        if not action_items:
            return

        # Build a set of already-saved IDs to avoid duplicates
        existing = {i.action_id for i in list_action_items(limit=1000)}

        for a in action_items:
            is_dict = isinstance(a, dict)
            action_id = a.get("action_id") if is_dict else getattr(a, "action_id", None)
            if not action_id or action_id in existing:
                continue

            priority = a.get("priority") if is_dict else getattr(a, "priority", "MEDIUM")
            if hasattr(priority, "value"):
                priority = priority.value  # Enum → string

            try:
                create_action_item(
                    action_id=action_id,
                    title=a.get("title") if is_dict else getattr(a, "title", ""),
                    description=a.get("description", "") if is_dict else getattr(a, "description", ""),
                    owner=a.get("owner", "Compliance") if is_dict else getattr(a, "owner", "Compliance"),
                    deadline=a.get("deadline", "") if is_dict else getattr(a, "deadline", ""),
                    priority=str(priority).upper(),
                    effort_days=int(a.get("effort_days", 1) if is_dict else getattr(a, "effort_days", 1)),
                    compliance_risk_score=int(a.get("compliance_risk_score", 5) if is_dict else getattr(a, "compliance_risk_score", 5)),
                    source_obligation_ids=list(a.get("source_obligation_ids", []) if is_dict else getattr(a, "source_obligation_ids", [])),
                    source_clauses=[],
                )
                existing.add(action_id)
            except Exception as e:
                logger.warning("action_item_save_failed", action_id=action_id, error=str(e))
    except Exception as e:
        logger.warning("save_action_items_failed", error=str(e))


async def _async_auto_notify(state, request) -> tuple[bool, list]:
    """
    Auto-trigger Slack alert and Jira tickets after pipeline completes.
    Slack fires if: risk_score >= 8 OR any CISA KEV advisory found.
    Jira fires for: all CRITICAL priority action items.
    Returns (slack_sent, jira_tickets_created).
    """
    risk_score = getattr(state, "overall_risk_score", 0)
    advisories = getattr(state, "security_advisories", []) or []
    action_items = getattr(state, "action_items", []) or []
    has_kev = any(
        (a.get("is_kev") if isinstance(a, dict) else getattr(a, "is_kev", False))
        for a in advisories
    )

    slack_sent = False
    jira_tickets = []

    # ── Auto Slack ────────────────────────────────────────────────────────────
    should_slack = risk_score >= 8 or has_kev
    webhook_url = getattr(settings, "slack_webhook_url", "")

    if should_slack and webhook_url:
        try:
            impact = getattr(state, "impact_summary", "") or ""
            gaps = getattr(state, "gaps", []) or []
            kev_note = " ⚠️ CISA Known Exploited Vulnerabilities detected." if has_kev else ""
            severity = "Critical" if risk_score >= 9 else "High"
            color = "#E5484D" if severity == "Critical" else "#F59E0B"
            emoji = "🔴" if severity == "Critical" else "🟠"

            payload = {
                "text": f"{emoji} *Red Forge Auto-Alert — {severity} Compliance Risk*",
                "attachments": [{
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Document:* `{request.document_id}`\n"
                                    f"*Jurisdiction:* `{request.jurisdiction}` · "
                                    f"*Risk Score:* `{risk_score}/10` · "
                                    f"*Severity:* `{severity}`\n\n"
                                    f"{impact}{kev_note}"
                                ),
                            },
                        },
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": (
                                f"Gaps: `{len(gaps)}` · "
                                f"CVEs: `{len(advisories)}` · "
                                f"Actions: `{len(action_items)}` · via Red Forge Auto-Monitor"
                            )}],
                        },
                    ],
                }],
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                slack_sent = resp.status_code == 200
                if not slack_sent:
                    logger.warning("auto_slack_failed", status=resp.status_code)
                else:
                    logger.info("auto_slack_sent", risk=risk_score, kev=has_kev)
        except Exception as e:
            logger.warning("auto_slack_error", error=str(e))
    elif should_slack:
        logger.info("auto_slack_skipped_no_webhook", risk=risk_score)

    # ── Auto Jira ─────────────────────────────────────────────────────────────
    should_jira = (
        settings.jira_base_url
        and settings.jira_api_token
        and any(
            (a.get("priority") if isinstance(a, dict) else getattr(a, "priority", "")).upper() == "CRITICAL"
            for a in action_items
        )
    )

    if should_jira:
        PRIORITY_MAP = {"CRITICAL": "Highest", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}
        project_key = settings.jira_project_key

        # Only auto-push CRITICAL items
        critical_items = [
            a for a in action_items
            if (a.get("priority") if isinstance(a, dict) else getattr(a, "priority", "")).upper() == "CRITICAL"
        ]

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                for item in critical_items[:5]:  # cap at 5 to avoid flooding
                    is_dict = isinstance(item, dict)
                    action_id = item.get("action_id") if is_dict else getattr(item, "action_id", "")
                    title = item.get("title", "") if is_dict else getattr(item, "title", "")
                    desc = item.get("description", "") if is_dict else getattr(item, "description", "")
                    priority = (item.get("priority", "CRITICAL") if is_dict else getattr(item, "priority", "CRITICAL"))
                    if hasattr(priority, "value"):
                        priority = priority.value

                    payload = {
                        "fields": {
                            "project": {"key": project_key},
                            "summary": f"[Auto] {title}",
                            "description": {
                                "type": "doc", "version": 1,
                                "content": [{"type": "paragraph", "content": [
                                    {"type": "text", "text": f"{desc}\n\nAuto-created by Red Forge · Document: {request.document_id}"}
                                ]}],
                            },
                            "issuetype": {"name": "Task"},
                            "priority": {"name": PRIORITY_MAP.get(priority.upper(), "Highest")},
                        }
                    }
                    resp = await client.post(
                        f"{settings.jira_base_url}/rest/api/3/issue",
                        json=payload,
                        auth=(settings.jira_email, settings.jira_api_token),
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 201:
                        jira_key = resp.json()["key"]
                        update_action_jira_ticket(action_id, jira_key)
                        jira_tickets.append({
                            "action_id": action_id,
                            "jira_key": jira_key,
                            "jira_url": f"{settings.jira_base_url}/browse/{jira_key}",
                        })
                        logger.info("auto_jira_created", action_id=action_id, jira_key=jira_key)
                    else:
                        logger.warning("auto_jira_failed", action_id=action_id, status=resp.status_code)
        except Exception as e:
            logger.warning("auto_jira_error", error=str(e))

    return slack_sent, jira_tickets


def _auto_notify(state, request) -> tuple[bool, list]:
    """Sync wrapper — runs async auto-notify in a new event loop (called from background thread)."""
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_async_auto_notify(state, request))
        finally:
            loop.close()
    except Exception as e:
        logger.warning("auto_notify_wrapper_error", error=str(e))
        return False, []


def _snapshot_obligations(state, request) -> None:
    """
    Snapshot extracted obligations for the regulation diff engine.
    Called after pipeline completes — stores a hash+snapshot in regulation_snapshots table.
    """
    try:
        from monitoring.regulation_differ import snapshot_and_diff

        obligations = getattr(state, "obligations", None) or (
            state.get("obligations") if isinstance(state, dict) else []
        )
        if not obligations:
            return

        source_id = getattr(request, "source_url", None) or getattr(request, "document_id", "unknown")
        jurisdiction = getattr(request, "jurisdiction", "") or ""
        regulatory_body = getattr(request, "regulatory_body", "") or ""

        diff = snapshot_and_diff(
            source_id=source_id,
            obligations=obligations,
            jurisdiction=jurisdiction,
            regulatory_body=regulatory_body,
        )

        if diff.get("has_changes") and not diff.get("is_new_regulation"):
            logger.info(
                "regulation_diff_detected",
                source_id=source_id,
                severity=diff.get("severity"),
                summary=diff.get("summary"),
            )
    except Exception as e:
        logger.warning("snapshot_obligations_error", error=str(e))


def _extract_node_logs(node_name: str, state: dict | object) -> list[str]:
    """Extract meaningful log lines from node output state."""
    if isinstance(state, dict):
        s = state
    else:
        s = state.__dict__ if hasattr(state, "__dict__") else {}

    logs = []
    if node_name == "scanner":
        logs.append(f"Relevance score: {s.get('relevance_score', 0):.2f}")
        logs.append(f"Relevant: {s.get('is_relevant', False)}")
        if s.get("sector"):
            logs.append(f"Sector: {s['sector']}")
    elif node_name == "extractor":
        obls = s.get("obligations", [])
        logs.append(f"Obligations extracted: {len(obls)}")
        logs.append(f"Confidence: {s.get('extraction_confidence', 0):.2f}")
        for o in (obls[:3] if isinstance(obls, list) else []):
            what = o.get("what", o.what if hasattr(o, "what") else "") if isinstance(o, dict) else getattr(o, "what", "")
            logs.append(f"OBL: {what[:60]}...")
    elif node_name == "impact_analyst":
        gaps = s.get("gaps", [])
        logs.append(f"Risk score: {s.get('overall_risk_score', 0)}/10")
        logs.append(f"Gaps found: {len(gaps)}")
        units = s.get("affected_business_units", [])
        if units:
            logs.append(f"Units affected: {', '.join(units[:3])}")
    elif node_name == "action_planner":
        actions = s.get("action_items", [])
        logs.append(f"Action items generated: {len(actions)}")
        for a in (actions[:2] if isinstance(actions, list) else []):
            title = a.get("title", getattr(a, "title", "")) if isinstance(a, dict) else getattr(a, "title", "")
            logs.append(f"Task: {title[:60]}")
    elif node_name == "validator":
        v = s.get("validation")
        if v:
            valid = v.get("valid", getattr(v, "valid", False)) if isinstance(v, dict) else getattr(v, "valid", False)
            confidence = v.get("confidence", getattr(v, "confidence", 0)) if isinstance(v, dict) else getattr(v, "confidence", 0)
            issues = v.get("issues", getattr(v, "issues", [])) if isinstance(v, dict) else getattr(v, "issues", [])
            if valid:
                logs.append(f"Validation passed · confidence {confidence:.2f}")
            else:
                logs.append(f"Validation issues: {len(issues)} — retrying")
        actions = s.get("action_items", [])
        if actions:
            logs.append(f"Output verified: {len(actions)} action items")
    return logs


@router.post("/search")
async def search_regulations(request: SearchRequest):
    """Semantic search over regulatory documents in Qdrant."""
    try:
        vector_store = RegulatoryVectorStore()
        filters = {}
        if request.jurisdiction:
            filters["jurisdiction"] = request.jurisdiction
        if request.regulatory_body:
            filters["regulatory_body"] = request.regulatory_body

        results = vector_store.search(
            query=request.query,
            limit=request.limit,
            filters=filters or None,
        )
        return {"results": results, "total": len(results)}
    except Exception as e:
        logger.error("search_failed", error=str(e))
        return {"results": [], "total": 0, "error": str(e)}


@router.get("/process/{document_id}/sync")
async def process_regulation_sync(document_id: str, raw_text: str = Query(...)):
    """Synchronous pipeline — waits for completion. Use for testing only."""
    orchestrator = ComplianceOrchestrator()
    result = orchestrator.process_document(
        document_id=document_id,
        raw_text=raw_text,
        source_url="",
        jurisdiction="UNKNOWN",
        regulatory_body="Unknown",
        document_type="GUIDANCE",
        published_date="",
    )
    return _serialize_result(result)


# ─── Live Feed ────────────────────────────────────────────────────────────────

EUR_LEX_RSS = "https://eur-lex.europa.eu/rss/legal-act-consolidated.xml"
FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"
SEBI_RSS = "https://www.sebi.gov.in/sebirss.xml"

RISK_KEYWORDS = {
    "Critical": ["critical", "mandatory", "penalty", "criminal", "immediate", "breach notification", "suspend"],
    "High": ["significant", "fine", "required", "must", "shall", "audit", "incident", "deadline"],
    "Medium": ["recommend", "should", "guidance", "update", "review"],
}

def _infer_severity(text: str) -> str:
    t = text.lower()
    for level, keywords in RISK_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return level
    return "Low"

def _infer_sector(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["bank", "payment", "fintech", "lending", "credit", "financial"]):
        return "Financial Services"
    if any(k in t for k in ["ai", "technology", "software", "cyber", "data"]):
        return "Technology"
    if any(k in t for k in ["health", "medical", "pharma"]):
        return "Healthcare"
    return "Financial Services"


async def _fetch_federal_register(jurisdiction_filter: str | None) -> list[dict]:
    """Fetch recent financial regulations from Federal Register API."""
    if jurisdiction_filter and jurisdiction_filter not in ("US", "All", "US_FEDERAL"):
        return []
    try:
        params = {
            "conditions[term]": "financial payment fintech compliance",
            "conditions[type][]": ["RULE", "PROPOSED_RULE", "NOTICE"],
            "per_page": 12,
            "order": "newest",
            "fields[]": ["document_number", "title", "abstract", "publication_date",
                         "agencies", "html_url", "document_type"],
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FEDERAL_REGISTER_API, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()

        items = []
        for doc in data.get("results", []):
            agencies = doc.get("agencies", [])
            regulator = agencies[0].get("short_name", "Federal Register") if agencies else "Federal Register"
            title = doc.get("title", "")
            abstract = doc.get("abstract", "") or ""
            pub_date = doc.get("publication_date", "")[:10]
            doc_type = {"RULE": "Final Rule", "PROPOSED_RULE": "Proposed Rule", "NOTICE": "Notice"}.get(
                doc.get("document_type", ""), "Notice"
            )
            severity = _infer_severity(title + " " + abstract)
            items.append({
                "id": doc.get("document_number", f"FR-{pub_date}"),
                "title": title[:120],
                "body": abstract[:250] if abstract else title,
                "jurisdiction": "US",
                "regulator": regulator,
                "date": pub_date,
                "severity": severity,
                "sector": _infer_sector(title + " " + abstract),
                "docType": doc_type,
                "rawText": f"{title}. {abstract}",
                "sourceUrl": doc.get("html_url", ""),
            })
        return items
    except Exception as e:
        logger.warning("federal_register_feed_failed", error=str(e))
        return []


async def _fetch_eur_lex(jurisdiction_filter: str | None) -> list[dict]:
    """Fetch recent EU regulations from EUR-Lex RSS."""
    if jurisdiction_filter and jurisdiction_filter not in ("EU", "All"):
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(EUR_LEX_RSS)
            if resp.status_code != 200:
                return []
            content = resp.text

        feed = feedparser.parse(content)
        items = []
        for entry in feed.entries[:8]:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            link = entry.get("link", "")
            pub = entry.get("published", "")[:10] if entry.get("published") else ""
            severity = _infer_severity(title + " " + summary)
            items.append({
                "id": entry.get("id", link)[-40:].replace("/", "-").strip("-"),
                "title": title[:120],
                "body": summary[:250] if summary else title,
                "jurisdiction": "EU",
                "regulator": "European Commission",
                "date": pub,
                "severity": severity,
                "sector": _infer_sector(title + " " + summary),
                "docType": "Regulation",
                "rawText": f"{title}. {summary}",
                "sourceUrl": link,
            })
        return items
    except Exception as e:
        logger.warning("eur_lex_feed_failed", error=str(e))
        return []


async def _fetch_sebi(jurisdiction_filter: str | None) -> list[dict]:
    """Fetch recent SEBI circulars from RSS feed."""
    if jurisdiction_filter and jurisdiction_filter not in ("India", "All", "INDIA"):
        return []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(SEBI_RSS, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            content = resp.text

        feed = feedparser.parse(content)
        items = []
        for entry in feed.entries[:8]:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or ""
            link = entry.get("link", "")
            pub = entry.get("published", "")[:10] if entry.get("published") else ""
            severity = _infer_severity(title + " " + summary)
            items.append({
                "id": entry.get("id", link)[-40:].replace("/", "-").strip("-"),
                "title": title[:120],
                "body": summary[:250] if summary else title,
                "jurisdiction": "India",
                "regulator": "SEBI",
                "date": pub,
                "severity": severity,
                "sector": _infer_sector(title + " " + summary),
                "docType": "Circular",
                "rawText": f"{title}. {summary}",
                "sourceUrl": link,
            })
        return items
    except Exception as e:
        logger.warning("sebi_feed_failed", error=str(e))
        return []


@router.get("/feed")
async def get_live_feed(jurisdiction: Optional[str] = Query(None)):
    """
    Live regulatory feed from Federal Register (US), EUR-Lex (EU), and SEBI (India).
    Returns real-time data — no hardcoded items.
    """
    us_items, eu_items, india_items = await asyncio.gather(
        _fetch_federal_register(jurisdiction),
        _fetch_eur_lex(jurisdiction),
        _fetch_sebi(jurisdiction),
    )

    all_items = us_items + eu_items + india_items

    # Sort by date descending (most recent first)
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    logger.info(
        "live_feed_served",
        us=len(us_items), eu=len(eu_items), india=len(india_items), total=len(all_items),
    )
    return {"items": all_items, "total": len(all_items), "live": True}
