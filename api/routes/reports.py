from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from typing import Optional
import structlog

from knowledge.graph.neo4j_client import Neo4jClient
from org_context.models.database import (
    list_controls,
    list_action_items,
    list_regulation_tracking,
    list_cve_alerts,
    list_audit_findings,
)

logger = structlog.get_logger()
router = APIRouter()


def _build_compliance_score() -> dict:
    """Inline compliance score calculation (mirrors compliance.py logic)."""
    from api.routes.compliance import _calculate_compliance_score
    try:
        return _calculate_compliance_score()
    except Exception as e:
        logger.error("report_compliance_score_failed", error=str(e))
        return {"score": 0, "risk_level": "CRITICAL", "error": str(e)}


def _build_controls_section() -> dict:
    """Fetch all controls from PostgreSQL and summarise coverage status."""
    try:
        controls = list_controls()
        items = []
        for c in controls:
            items.append({
                "control_id": c.control_id,
                "name": c.name,
                "framework": c.framework.value if c.framework else None,
                "coverage_score": c.coverage_score,
                "is_automated": c.is_automated,
                "owner_email": c.owner_email,
                "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            })

        total = len(items)
        high_coverage = sum(1 for i in items if (i["coverage_score"] or 0) >= 0.8)
        low_coverage = sum(1 for i in items if (i["coverage_score"] or 0) < 0.5)

        return {
            "controls": items,
            "total": total,
            "high_coverage_count": high_coverage,
            "low_coverage_count": low_coverage,
        }
    except Exception as e:
        logger.error("report_controls_failed", error=str(e))
        return {"controls": [], "total": 0, "error": str(e)}


def _build_action_items_section() -> dict:
    """Fetch all open action items grouped by priority."""
    try:
        all_items = list_action_items(limit=10000)
        open_items = [a for a in all_items if (a.status or "").lower() not in ("completed", "waived")]

        grouped = {}
        for item in open_items:
            priority = (item.priority or "UNSET").upper()
            if priority not in grouped:
                grouped[priority] = []
            grouped[priority].append({
                "action_id": item.action_id,
                "title": item.title,
                "owner": item.owner,
                "deadline": item.deadline,
                "priority": item.priority,
                "status": item.status,
                "compliance_risk_score": item.compliance_risk_score,
            })

        return {
            "open_action_items_by_priority": grouped,
            "total_open": len(open_items),
            "total_all": len(all_items),
        }
    except Exception as e:
        logger.error("report_action_items_failed", error=str(e))
        return {"open_action_items_by_priority": {}, "total_open": 0, "error": str(e)}


def _build_regulation_tracking_section(source_id: Optional[str] = None) -> dict:
    """Fetch regulation tracking status."""
    try:
        all_regs = list_regulation_tracking(limit=10000)
        if source_id:
            all_regs = [r for r in all_regs if r.source_id == source_id]

        items = []
        for r in all_regs:
            items.append({
                "source_id": r.source_id,
                "title": r.title,
                "jurisdiction": r.jurisdiction,
                "regulatory_body": r.regulatory_body,
                "is_relevant": r.is_relevant,
                "relevance_score": r.relevance_score,
                "overall_risk_score": r.overall_risk_score,
                "processing_status": r.processing_status,
                "published_date": r.published_date.isoformat() if r.published_date else None,
                "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            })

        return {
            "regulations": items,
            "total": len(items),
            "relevant_count": sum(1 for i in items if i["is_relevant"]),
        }
    except Exception as e:
        logger.error("report_regulation_tracking_failed", error=str(e))
        return {"regulations": [], "total": 0, "error": str(e)}


def _build_cve_section() -> dict:
    """Fetch active CVE alerts."""
    try:
        all_cves = list_cve_alerts(limit=10000)
        active = [c for c in all_cves if not c.jira_key]
        items = []
        for c in all_cves:
            items.append({
                "cve_id": c.cve_id,
                "cvss_score": c.cvss_score,
                "severity": c.severity,
                "category": c.category,
                "description": (c.description or "")[:300],
                "affected_packages": c.affected_packages,
                "is_kev": c.is_kev,
                "jira_key": c.jira_key,
                "first_seen": c.first_seen.isoformat() if c.first_seen else None,
            })

        return {
            "cve_alerts": items,
            "total": len(items),
            "active_count": len(active),
        }
    except Exception as e:
        logger.error("report_cve_alerts_failed", error=str(e))
        return {"cve_alerts": [], "total": 0, "error": str(e)}


def _build_gaps_section() -> dict:
    """Query Neo4j for compliance gaps — obligations with low or missing control coverage."""
    try:
        neo4j = Neo4jClient()
        query = """
        MATCH (o:Obligation)
        OPTIONAL MATCH (c:ComplianceControl)-[r:ADDRESSES]->(o)
        WITH o, avg(r.coverage_pct) AS avg_coverage, count(c) AS control_count
        WHERE avg_coverage IS NULL OR avg_coverage < 80
        RETURN o.id AS obligation_id,
               o.what AS requirement,
               coalesce(avg_coverage, 0) AS coverage_pct,
               control_count
        ORDER BY coverage_pct ASC
        LIMIT 50
        """
        gaps = neo4j.run_cypher(query)
        return {"gaps": gaps, "total": len(gaps)}
    except Exception as e:
        logger.error("report_gaps_failed", error=str(e))
        return {"gaps": [], "total": 0, "error": str(e)}


def _build_risk_summary(score_data: dict) -> dict:
    """Produce a risk summary from the compliance score data."""
    breakdown = score_data.get("breakdown", {})
    risks = []

    control_pct = breakdown.get("control_coverage", {}).get("pct", 0)
    if control_pct < 50:
        risks.append({
            "area": "Control Coverage",
            "level": "CRITICAL" if control_pct < 30 else "HIGH",
            "detail": f"Control coverage is at {control_pct}%, well below acceptable threshold.",
        })

    action_info = breakdown.get("action_completion", {})
    if action_info.get("open", 0) > 10:
        risks.append({
            "area": "Open Action Items",
            "level": "HIGH",
            "detail": f"{action_info['open']} action items remain open.",
        })

    cve_info = breakdown.get("cve_resolved", {})
    if cve_info.get("unresolved_cves", 0) > 0:
        risks.append({
            "area": "Unresolved CVEs",
            "level": "HIGH" if cve_info["unresolved_cves"] > 5 else "MEDIUM",
            "detail": f"{cve_info['unresolved_cves']} CVEs are unresolved.",
        })

    return {"risks": risks, "total_risks": len(risks)}


@router.get("/audit")
async def generate_audit_report():
    """Generate a full compliance audit report with all data aggregated."""
    try:
        report_id = str(uuid4())
        generated_at = datetime.utcnow().isoformat() + "Z"

        score_data = _build_compliance_score()

        report = {
            "report_metadata": {
                "report_id": report_id,
                "generated_at": generated_at,
                "report_type": "full_audit",
            },
            "compliance_score": score_data,
            "controls": _build_controls_section(),
            "action_items": _build_action_items_section(),
            "regulation_tracking": _build_regulation_tracking_section(),
            "cve_alerts": _build_cve_section(),
            "gaps": _build_gaps_section(),
            "risk_summary": _build_risk_summary(score_data),
        }

        logger.info("audit_report_generated", report_id=report_id)
        return report
    except Exception as e:
        logger.error("audit_report_failed", error=str(e))
        return {
            "report_metadata": {
                "report_id": str(uuid4()),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "report_type": "full_audit",
                "error": str(e),
            },
        }


@router.get("/audit/regulation/{source_id:path}")
async def generate_regulation_audit_report(source_id: str):
    """Generate an audit report scoped to a specific regulation by source_id."""
    try:
        report_id = str(uuid4())
        generated_at = datetime.utcnow().isoformat() + "Z"

        # Get regulation-specific tracking data
        reg_section = _build_regulation_tracking_section(source_id=source_id)
        if reg_section.get("total", 0) == 0:
            raise HTTPException(404, f"Regulation with source_id '{source_id}' not found")

        # Get obligations and controls for this regulation from Neo4j
        obligations = []
        related_controls = []
        try:
            neo4j = Neo4jClient()
            ob_query = """
            MATCH (r:Regulation {source_id: $source_id})-[:REQUIRES]->(o:Obligation)
            RETURN o.id AS obligation_id,
                   o.what AS requirement,
                   o.deadline AS deadline,
                   o.penalty AS penalty
            """
            obligations = neo4j.run_cypher(ob_query, {"source_id": source_id})

            ctrl_query = """
            MATCH (r:Regulation {source_id: $source_id})-[:REQUIRES]->(o:Obligation)
            OPTIONAL MATCH (c:ComplianceControl)-[addr:ADDRESSES]->(o)
            RETURN o.id AS obligation_id,
                   c.id AS control_id,
                   c.name AS control_name,
                   c.framework AS framework,
                   addr.coverage_pct AS coverage_pct
            """
            related_controls = neo4j.run_cypher(ctrl_query, {"source_id": source_id})
        except Exception as e:
            logger.error("regulation_audit_neo4j_failed", source_id=source_id, error=str(e))

        # Get action items linked to this regulation
        reg_action_items = []
        try:
            all_actions = list_action_items(limit=10000)
            # Filter to actions whose source_obligation_ids overlap with this regulation's obligations
            ob_ids = {ob.get("obligation_id") for ob in obligations if ob.get("obligation_id")}
            for a in all_actions:
                src_obs = a.source_obligation_ids or []
                if any(oid in ob_ids for oid in src_obs):
                    reg_action_items.append({
                        "action_id": a.action_id,
                        "title": a.title,
                        "priority": a.priority,
                        "status": a.status,
                        "owner": a.owner,
                        "deadline": a.deadline,
                    })
        except Exception as e:
            logger.error("regulation_audit_actions_failed", source_id=source_id, error=str(e))

        report = {
            "report_metadata": {
                "report_id": report_id,
                "generated_at": generated_at,
                "report_type": "regulation_audit",
                "source_id": source_id,
            },
            "regulation": reg_section.get("regulations", [{}])[0] if reg_section.get("regulations") else {},
            "obligations": obligations,
            "controls": related_controls,
            "action_items": reg_action_items,
        }

        logger.info("regulation_audit_report_generated", report_id=report_id, source_id=source_id)
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("regulation_audit_report_failed", source_id=source_id, error=str(e))
        return {
            "report_metadata": {
                "report_id": str(uuid4()),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "report_type": "regulation_audit",
                "source_id": source_id,
                "error": str(e),
            },
        }
